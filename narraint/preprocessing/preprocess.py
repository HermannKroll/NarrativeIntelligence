import logging
import os
import tempfile
import sys
import shutil
from argparse import ArgumentParser
from typing import List
import multiprocessing

from narraint.entity import enttypes
from narraint.backend.database import Session
from narraint.entity.enttypes import TAG_TYPE_MAPPING
from narraint.backend.export import export
from narraint.backend.load import load
from narraint.backend.models import DocTaggedBy
from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.config import Config
from narraint.preprocessing.tagging.base import BaseTagger
from narraint.preprocessing.tagging.dnorm import DNorm
from narraint.preprocessing.tagging.dosage import DosageFormTagger
from narraint.preprocessing.tagging.gnormplus import GNormPlus
from narraint.preprocessing.tagging.taggerone import TaggerOne
from narraint.preprocessing.tagging.tmchem import TMChem
from narraint.pubtator.document import get_document_id, DocumentError
from narraint.pubtator.distribute import distribute_workload, create_parallel_dirs, split_composites
from narraint.pubtator.sanitize import sanitize

LOGGING_FORMAT = '%(asctime)s %(levelname)s %(threadName)s %(module)s:%(lineno)d %(message)s'


def init_sqlalchemy_logger(log_filename, log_level=logging.INFO):
    formatter = logging.Formatter(LOGGING_FORMAT)
    logger = logging.getLogger('sqlalchemy.engine')
    logger.setLevel(log_level)
    logger.propagate = False
    fh = logging.FileHandler(log_filename, mode="a+")
    fh.setLevel(log_level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


def init_preprocess_logger(log_filename, log_level, log_format=LOGGING_FORMAT, worker_id: int = None):
    formatter = logging.Formatter(log_format)
    logger = logging.getLogger("preprocess" if worker_id is None else f"preprocess-w{worker_id}")
    logger.setLevel("DEBUG")
    logger.propagate = False
    fh = logging.FileHandler(log_filename, mode="a+")
    fh.setLevel("DEBUG")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def get_tagger_by_ent_type(tag_types, use_tagger_one):
    tagger_by_ent_type = {}
    if enttypes.GENE in tag_types:
        tagger_by_ent_type[enttypes.GENE] = GNormPlus
        if enttypes.SPECIES not in tag_types:
            raise ValueError("GNormPlus does not support tagging of Species and Genes separately")
    if enttypes.SPECIES in tag_types:
        tagger_by_ent_type[enttypes.SPECIES] = GNormPlus
        if enttypes.GENE not in tag_types:
            raise ValueError("GNormPlus does not support tagging of Species and Genes separately")

    if enttypes.DISEASE in tag_types and not use_tagger_one:
        tagger_by_ent_type[enttypes.DISEASE] = DNorm
    if enttypes.CHEMICAL in tag_types and not use_tagger_one:
        tagger_by_ent_type[enttypes.CHEMICAL] = TMChem
    if enttypes.CHEMICAL in tag_types and enttypes.DISEASE in tag_types and use_tagger_one:
        tagger_by_ent_type[enttypes.CHEMICAL] = TaggerOne
        tagger_by_ent_type[enttypes.DISEASE] = TaggerOne
    if (enttypes.CHEMICAL not in tag_types or enttypes.DISEASE not in tag_types) and use_tagger_one:
        raise ValueError("TaggerOne does not support Tagging of Chemicals or Diseases separately!")
    if enttypes.DOSAGE_FORM in tag_types:
        tagger_by_ent_type[enttypes.DOSAGE_FORM] = DosageFormTagger

    return tagger_by_ent_type


def get_untagged_doc_ids_by_ent_type(collection, target_ids, ent_type, tagger_cls, logger):
    session = Session.get()
    result = session.query(DocTaggedBy).filter(
        DocTaggedBy.document_id.in_(target_ids),
        DocTaggedBy.document_collection == collection,
        DocTaggedBy.ent_type == ent_type,
        DocTaggedBy.tagger_name == tagger_cls.__name__,
        DocTaggedBy.tagger_version == tagger_cls.__version__,
    ).values(DocTaggedBy.document_id)
    present_ids = set(x[0] for x in result)
    logger.debug(
        "Retrieved {} ids (ent_type={},collection={},tagger={}/{})".format(
            len(present_ids), ent_type, collection, tagger_cls.__name__, tagger_cls.__version__
        ))
    missing_ids = target_ids.difference(present_ids)
    return missing_ids


def preprocess(collection, root_dir, input_dir, log_dir, logger, output_filename, conf, *tag_types,
               resume=False, use_tagger_one=False):
    """
    Method creates a single PubTator file with the documents from in ``in_dir`` and its tags.

    :param logger: Logger instance
    :param log_dir: Directory for logs
    :param root_dir: Root directory (i.e., working directory)
    :param input_dir: Input directory containing PubTator files to tag
    :param collection: Collection ID (e.g., PMC)
    :param use_tagger_one: Flag to use TaggerOne instead of tmChem and DNorm
    :param output_filename: Filename of PubTator to create
    :param conf: config object
    :param resume: flag, if method should resume (if True, tag_genes, tag_chemicals and tag_diseases must
    be set accordingly)
    """
    logger.info("=== STEP 1 - Preparation ===")
    target_ids = set()
    mapping_id_file = dict()
    mapping_file_id = dict()
    missing_files_type = dict()

    # Get tagger classes
    tagger_by_ent_type = get_tagger_by_ent_type(tag_types, use_tagger_one)

    # Gather target IDs
    for fn in os.listdir(input_dir):
        abs_path = os.path.join(input_dir, fn)
        try:
            doc_id = get_document_id(abs_path)
            target_ids.add(doc_id)
            mapping_id_file[doc_id] = abs_path
            mapping_file_id[abs_path] = doc_id
        except DocumentError as e:
            logger.warning(e)
    logger.info("Preprocessing {} documents".format(len(target_ids)))

    # Get input documents for each tagger
    for tag_type in tag_types:
        tagger_cls = tagger_by_ent_type[tag_type]
        missing_ids = get_untagged_doc_ids_by_ent_type(collection, target_ids, tag_type, tagger_cls, logger)
        missing_files_type[tag_type] = frozenset(mapping_id_file[x] for x in missing_ids)
        task_list_fn = os.path.join(root_dir, "tasklist_{}.txt".format(tag_type.lower()))
        with open(task_list_fn, "w") as f:
            f.write("\n".join(missing_files_type[tag_type]))
        logger.debug("Tasklist for {} written to: {}".format(tag_type, task_list_fn))
        logger.info("Tasklist for {} contains {} documents".format(tag_type, len(missing_ids)))

    # Init taggers
    kwargs = dict(collection=collection, root_dir=root_dir, input_dir=input_dir, logger=logger,
                  log_dir=log_dir, config=conf, mapping_id_file=mapping_id_file, mapping_file_id=mapping_file_id)
    taggers: List[BaseTagger] = [tagger_cls(**kwargs) for tagger_cls in set(tagger_by_ent_type.values())]
    for tagger in taggers:
        logger.info("Preparing {}".format(tagger.name))
        for target_type in tagger.TYPES:
            tagger.add_files(*missing_files_type[target_type])
        tagger.prepare(resume)
    logger.info("=== STEP 2 - Tagging ===")
    for tagger in taggers:
        logger.info("Starting {}".format(tagger.name))
        tagger.start()
    for tagger in taggers:
        tagger.join()
    logger.info("=== STEP 3 - Post-processing ===")
    for tagger in taggers:
        logger.info("Finalizing {}".format(tagger.name))
        tagger.finalize()
    export(output_filename, tag_types, target_ids, collection=collection, content=True, logger=logger)
    logger.info("=== Finished ===")


def main():
    parser = ArgumentParser(description="Preprocess PubMedCentral files for the use with Snorkel")

    parser.add_argument("--resume", action="store_true", help="Resume tagging")
    parser.add_argument("--composite", action="store_true",
                        help="Check for composite pubtator files in input. Automatically enabled if input is a file.")

    group_tag = parser.add_argument_group("Tagging")
    parser.add_argument("-t", "--tag", choices=TAG_TYPE_MAPPING.keys(), nargs="+", required=True)
    parser.add_argument("-c", "--corpus", required=True)
    group_tag.add_argument("--tagger-one", action="store_true",
                           help="Tag diseases and chemicals with TaggerOne instead of DNorm and tmChem.")

    group_settings = parser.add_argument_group("Settings")
    group_settings.add_argument("--config", default=PREPROCESS_CONFIG,
                                help="Configuration file (default: {})".format(PREPROCESS_CONFIG))
    group_settings.add_argument("--loglevel", default="INFO")
    group_settings.add_argument("--workdir", default=None)
    group_settings.add_argument("--skip-load", action='store_true',
                                help="Skip bulk load of documents on start (expert setting)")
    group_settings.add_argument("-w", "--workers", default=1, help="Number of processes for parallelized preprocessing",
                                type=int)

    parser.add_argument("input", help="Directory with PubTator files ", metavar="IN_DIR")
    parser.add_argument("output", help="Output file", metavar="OUT_FILE")
    args = parser.parse_args()

    # Create configuration wrapper
    conf = Config(args.config)

    # Prepare directories and logging
    root_dir = os.path.abspath(args.workdir) if args.workdir or args.resume else tempfile.mkdtemp()
    ext_in_dir = args.input
    in_dir = os.path.join(root_dir, "input")
    log_dir = os.path.abspath(os.path.join(root_dir, "log"))
    if not os.path.exists(root_dir):
        os.makedirs(root_dir)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    if not os.path.exists(in_dir):
        os.makedirs(in_dir)
    logger = init_preprocess_logger(os.path.join(log_dir, "preprocessing.log"), args.loglevel.upper())

    init_sqlalchemy_logger(os.path.join(log_dir, "sqlalchemy.log"), args.loglevel.upper())
    logger.info("Project directory: {}".format(root_dir))
    logger.debug("Input directory: {}".format(in_dir))
    if not os.path.exists(in_dir):
        logger.error("Fatal: Input directory or file not found")
        sys.exit(1)

    if args.composite or os.path.isfile(ext_in_dir):
        logger.debug(f"Composite of single input file: created input directory at {in_dir}")
        logger.info(f"Composite enabled or single file as input. Splitting up composite files...")
        split_composites(ext_in_dir, in_dir, logger=logger)
        logger.info("done. Sanitizing files...")
        logger.info()
        ignored, sanitized = sanitize(in_dir, delete_mismatched=True)
    else:
        ignored, sanitized = sanitize(ext_in_dir, output_dir=in_dir)
    logger.info(f"{len(ignored)} files ignored because of wrong format or missing abstract")
    logger.info(f"{len(sanitized)} files sanitized")


    # Add documents to database
    if args.skip_load:
        logger.info("Skipping bulk load")
    else:
        load(in_dir, args.corpus, logger=logger)
    # Create list of tagging ent types
    tag_types = enttypes.ENT_TYPES_SUPPORTED_BY_TAGGERS if "A" in args.tag else [TAG_TYPE_MAPPING[x] for x in args.tag]

    # Run actual preprocessing
    if args.workers > 1:
        logger.info('splitting up workload for multiple threads')
        distribute_workload(in_dir, os.path.join(root_dir, "inputDirs"), int(args.workers))
        create_parallel_dirs(root_dir, int(args.workers), "worker")
        create_parallel_dirs(log_dir, int(args.workers), "worker")
        processes = []
        output_paths = []
        for n in range(int(args.workers)):
            sub_in_dir = os.path.join(root_dir, "inputDirs", f"batch{n}")
            sub_root_dir = os.path.join(root_dir, f"worker{n}")
            sub_log_dir = os.path.join(log_dir, f"worker{n}")
            sub_logger = init_preprocess_logger(
                os.path.join(sub_log_dir, "preprocessing.log"),
                args.loglevel.upper(),
                worker_id=n,
                log_format='%(asctime)s %(levelname)s %(name)s %(module)s:%(lineno)d %(message)s')
            sub_logger.propagate = False
            sub_output = os.path.join(sub_root_dir, "output.txt")
            output_paths.append(sub_output)
            process_args = (
                args.corpus, sub_root_dir, sub_in_dir, sub_log_dir, sub_logger,
                sub_output, conf, *tag_types
            )
            kwargs = dict(resume=args.resume, use_tagger_one=args.tagger_one)
            process = multiprocessing.Process(target=preprocess, args=process_args, kwargs=kwargs)
            processes.append(process)
            process.start()
        for process in processes:
            process.join()
        # merge output files
        logger.info(f"merging sub output files to {args.output}")
        with open(args.output, "w+") as output_file:
            for sub_out_path in output_paths:
                with open(sub_out_path) as sub_out_file:
                    for line in sub_out_file:
                        output_file.write(line)
                os.remove(sub_out_path)
    else:
        preprocess(args.corpus, root_dir, in_dir, log_dir, logger, args.output, conf, *tag_types,
                   resume=args.resume, use_tagger_one=args.tagger_one)

    if not args.workdir:
        logger.info("Done. Deleting tmp project directory.")
        shutil.rmtree(root_dir)


if __name__ == "__main__":
    main()
