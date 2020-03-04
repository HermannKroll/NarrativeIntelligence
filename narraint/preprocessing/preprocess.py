import logging
import os
import tempfile
from argparse import ArgumentParser
from shutil import copy
from typing import List
import multiprocessing

from narraint.backend import enttypes
from narraint.backend.database import Session
from narraint.backend.enttypes import TAG_TYPE_MAPPING
from narraint.backend.export import export
from narraint.backend.load import bulk_load
from narraint.backend.models import DocTaggedBy
from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.collect import PMCCollector
from narraint.preprocessing.config import Config
from narraint.preprocessing.convertids import load_pmcids_to_pmid_index
from narraint.preprocessing.tagging.base import BaseTagger
from narraint.preprocessing.tagging.dnorm import DNorm
from narraint.preprocessing.tagging.dosage import DosageFormTagger
from narraint.preprocessing.tagging.gnormplus import GNormPlus
from narraint.preprocessing.tagging.taggerone import TaggerOne
from narraint.preprocessing.tagging.tmchem import TMChem
from narraint.pubtator.convert import PMCConverter
from narraint.pubtator.count import count_documents
from narraint.pubtator.document import get_document_id, DocumentError
from narraint.pubtator.split import split

LOGGING_FORMAT = '%(asctime)s %(levelname)s %(threadName)s %(module)s:%(lineno)d %(message)s'


def init_sqlalchemy_logger(log_filename, log_level=logging.INFO):
    formatter = logging.Formatter(LOGGING_FORMAT)
    logger = logging.getLogger('sqlalchemy.engine')
    logger.setLevel(log_level)
    fh = logging.FileHandler(log_filename, mode="a+")
    fh.setLevel(log_level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


def init_preprocess_logger(log_filename, log_level):
    formatter = logging.Formatter(LOGGING_FORMAT)
    logger = logging.getLogger("preprocessing")
    logger.setLevel("DEBUG")
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
    if enttypes.DISEASE in tag_types and not use_tagger_one:
        tagger_by_ent_type[enttypes.DISEASE] = DNorm
    if enttypes.CHEMICAL in tag_types and not use_tagger_one:
        tagger_by_ent_type[enttypes.CHEMICAL] = TMChem
    if enttypes.CHEMICAL in tag_types and enttypes.DISEASE in tag_types and use_tagger_one:
        tagger_by_ent_type[enttypes.CHEMICAL] = TaggerOne
        tagger_by_ent_type[enttypes.DISEASE] = TaggerOne
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

def create_parallel_dirs(root, number, prefix, *subdirs):
    """
    Creates number identical subdirectories named <prefix><index> containing subdirectories specified with the names
    given in *subdirs.
    :param root: The directory where the subdirectories are to be created
    :param number: The number of identical subdirs to be created
    :param prefix: The prefix in the name of the subdirs
    :param subdirs: The subdirectories to be contained by each identical directory
    """
    for n in range(number):
        indexed_dir = os.path.join(root, f"{prefix}{n}")
        if not os.path.exists(indexed_dir):
            os.makedirs(indexed_dir)
        for name in subdirs:
            subdir_path = os.path.join(root, f"{prefix}{n}", name)
            if not os.path.exists(subdir_path):
                os.makedirs(subdir_path)

def distribute_workload(input_dir, output_root, workers_number:int, subdirs_name="batch", ):
    """
    Takes an input directory filled with files, each containing one or multiple pubtator documents. Then creates
    workers_number subdirectories in output_root and distributes the documents equally among them.
    The files in input_dir will be copied.
    :param input_dir: dictionary containing the files to be distributed (single pubtator document or multiple in one)
    :param output_root: path where the the subdirectories for every worker will be created
    :param workers_number: the number of workers to distribute the workload on
    :param subdirs_name: the prefix to the batch subdirs
    """
    #create subdirectories
    tmp_path = os.path.join(output_root, "tmp")
    os.makedirs(tmp_path)
    create_parallel_dirs(output_root, workers_number, subdirs_name)
    paths = (os.path.join(input_dir, file) for file in os.listdir(input_dir))
    file_sizes = {path: os.path.getsize(path) for path in paths if os.path.isfile(path)}
    total_workload = sum(file_sizes.values())
    workload_per_worker = total_workload // (workers_number-1)

    current_worker_id=0
    current_worker_workload=0
    for file, file_size in file_sizes.items():
        #TODO: check after adding -> too much workload, checking before adding -> leftover workload. to be fixed
        if file_size < workload_per_worker:
            copy(file, os.path.join(output_root,f"{subdirs_name}{current_worker_id}"))
            current_worker_workload += file_size
            if current_worker_workload > workload_per_worker:
                current_worker_id = (current_worker_id+1)%workers_number
                current_worker_workload=0
        else:
            avg_size_per_doc = file_size//count_documents(file)
            batch_size = workload_per_worker//avg_size_per_doc
            split(file,tmp_path,batch_size)
            current_worker_id = (current_worker_id + 1) % workers_number
            for batch in os.listdir(tmp_path):
                batch = os.path.join(tmp_path,batch)
                os.rename(batch, os.path.join(output_root,f"{subdirs_name}{current_worker_id}",os.path.basename(batch)))
                current_worker_id = (current_worker_id + 1) % workers_number
            current_worker_workload=0


def preprocess(collection, root_dir, input_dir, log_dir, logger, output_filename, conf, *tag_types,
               resume=False, use_tagger_one=False, verbose=True):
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
    if verbose: print("=== STEP 1 - Preparation ===")
    target_ids = set()
    mapping_id_file = dict()
    mapping_file_id = dict()
    missing_files_type = dict()

    # Get tagger classes
    tagger_by_ent_type = get_tagger_by_ent_type(tag_types, use_tagger_one)

    if not verbose:
        logger.setLevel(logging.WARNING)

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
    kwargs = dict(collection=collection, root_dir=root_dir, input_dir=input_dir,
                  log_dir=log_dir, config=conf, mapping_id_file=mapping_id_file, mapping_file_id=mapping_file_id)
    taggers: List[BaseTagger] = [tagger_cls(**kwargs) for tagger_cls in set(tagger_by_ent_type.values())]
    for tagger in taggers:
        logger.info("Preparing {}".format(tagger.name))
        for target_type in tagger.TYPES:
            tagger.add_files(*missing_files_type[target_type])
        tagger.prepare(resume)
    if verbose: print("=== STEP 2 - Tagging ===")
    for tagger in taggers:
        logger.info("Starting {}".format(tagger.name))
        tagger.start()
    for tagger in taggers:
        tagger.join()
    if verbose: print("=== STEP 3 - Post-processing ===")
    for tagger in taggers:
        logger.info("Finalizing {}".format(tagger.name))
        tagger.finalize()
    export(output_filename, tag_types, target_ids, collection=collection, content=True)
    if verbose: print("=== Finished ===")


def main():
    parser = ArgumentParser(description="Preprocess PubMedCentral files for the use with Snorkel")

    parser.add_argument("--resume", action="store_true", help="Resume tagging")
    parser.add_argument("--ids", action="store_true",
                        help="Collect documents from directory (e.g., for PubMedCentral) and convert to PubTator")

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
    group_settings.add_argument("-w", "--workers",default=1, help="Number of processes for parallelized preprocessing",
                                type=int)

    parser.add_argument("input", help="Directory with PubTator files "
                                      "(can be a file if --ids is set or a directory if --resume is set)",
                        metavar="IN_DIR")
    parser.add_argument("output", help="Output file", metavar="OUT_FILE")
    args = parser.parse_args()

    # Create configuration wrapper
    conf = Config(args.config)

    # Prepare directories and logging
    root_dir = os.path.abspath(args.workdir) if args.workdir or args.resume else tempfile.mkdtemp()
    in_dir = os.path.abspath(args.input)
    log_dir = os.path.abspath(os.path.join(root_dir, "log"))
    if not os.path.exists(root_dir):
        os.mkdir(root_dir)
    if not os.path.exists(in_dir):
        os.mkdir(in_dir)
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    logger = init_preprocess_logger(os.path.join(log_dir, "preprocessing.log"), args.loglevel.upper())
    init_sqlalchemy_logger(os.path.join(log_dir, "sqlalchemy.log"), args.loglevel.upper())
    logger.info("Project directory: {}".format(root_dir))
    logger.debug("Input directory: {}".format(in_dir))

    # Perform collection and conversion
    if args.ids and args.corpus == "PMC":
        logger.info('Load PMCID to PMID translation file')
        pmcid2pmid = load_pmcids_to_pmid_index(conf.pmcid2pmid)
        in_dir = tempfile.mkdtemp()
        error_file = os.path.join(in_dir, "conversion_errors.txt")
        collector = PMCCollector(conf.pmc_dir)
        files = collector.collect(args.input)
        translator = PMCConverter()
        translator.convert_bulk(files, in_dir, pmcid2pmid, error_file)
    elif args.ids:
        raise logger.exception("Providing an ID set is only supported for PMC collection")


    # Add documents to database
    if args.skip_load:
        logger.info("Skipping bulk load")
    else:
        bulk_load(in_dir, args.corpus, logger)
    # Create list of tagging ent types
    tag_types = enttypes.ALL if "A" in args.tag else [TAG_TYPE_MAPPING[x] for x in args.tag]

    # Run actual preprocessing
    if not args.workers <= 1:
        logger.info('splitting up workload for multiple threads')
        distribute_workload(in_dir,os.path.join(root_dir,"inputDirs"),int(args.workers))
        create_parallel_dirs(root_dir,int(args.workers),"worker", "log")
        processes=[]
        for n in range(int(args.workers)):
            sub_in_dir=os.path.join(root_dir, "inputDirs", f"batch{n}")
            sub_root_dir=os.path.join(root_dir, f"worker{n}")
            sub_log_dir=os.path.join(sub_root_dir, "log")
            sub_logger = init_preprocess_logger(os.path.join(sub_log_dir,"preprocessing.log"), args.loglevel.upper())
            process_args = (args.corpus, sub_root_dir, sub_in_dir, sub_log_dir, sub_logger, args.output, conf, *tag_types)
            kwargs = dict(resume=args.resume, use_tagger_one=args.tagger_one, verbose=False)
            process=multiprocessing.Process(target = preprocess, args=process_args, kwargs=kwargs)
            processes.append(process)
            process.start()
        map(lambda p: p.join(), processes)
    else:
        preprocess(args.corpus, root_dir, in_dir, log_dir, logger, args.output, conf, *tag_types,
                   resume=args.resume, use_tagger_one=args.tagger_one)

if __name__ == "__main__":
    main()
