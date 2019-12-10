import logging
import os
import pprint
import re
import tempfile
from argparse import ArgumentParser

from narraint.backend import types
from narraint.backend.database import Session
from narraint.backend.export import export
from narraint.backend.load import bulk_load
from narraint.backend.models import Document, Tag
from narraint.backend.types import TAG_TYPE_MAPPING
from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.config import Config
from narraint.preprocessing.tagging.dnorm import DNorm
from narraint.preprocessing.tagging.dosage import DosageFormTagger
from narraint.preprocessing.tagging.gnorm import GNorm
from narraint.preprocessing.tagging.taggerone import TaggerOne
from narraint.preprocessing.tagging.tmchem import TMChem
from narraint.preprocessing.translate import PMCCollector, PMCTranslator

LOGGING_FORMAT = '%(asctime)s %(levelname)s %(threadName)s %(module)s:%(lineno)d %(message)s'
REGEX_PUBTATOR_ID = re.compile(r"(\d+)\|t\|")


def init_logger(log_filename, log_level):
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


def rename_input_files(translation_dir, logger):
    for fn in os.listdir(translation_dir):
        if not fn.startswith(".") and not fn.endswith("/"):
            doc_id = re.search(r"\d+", fn)
            if doc_id:
                target_name = "PMC{}.txt".format(doc_id.group())
                if fn != target_name:
                    os.rename(os.path.join(translation_dir, fn), os.path.join(translation_dir, target_name))
            else:
                os.remove(os.path.join(translation_dir, fn))
                logger.debug("Removing file {}: No ID found".format(fn))


def get_id(fn):
    with open(fn) as f:
        line = f.readline()
    match = REGEX_PUBTATOR_ID.match(line)
    return int(match.group(1))


def preprocess(corpus, in_dir, output_filename, conf, *tag_types,
               resume=False, console_log_level="INFO", workdir=None, use_tagger_one=False):
    """
    Method creates a full-tagged PubTator file with the documents from in ``input_file_dir_list``.
    Method expects an ID file or an ID list if resume=False.
    Method expects the working directory (temp-directory) of the processing to resume if resume=True.

    :param use_tagger_one:
    :param workdir: Working directory
    :param console_log_level: Log level for console output
    :param output_filename: Filename of PubTator to create
    :param conf: config object
    :param resume: flag, if method should resume (if True, tag_genes, tag_chemicals and tag_diseases must
    be set accordingly)
    """
    print("=== STEP 1 - Preparation ===")
    root_dir = os.path.abspath(workdir) if workdir or resume else tempfile.mkdtemp()
    input_dir = in_dir  # os.path.abspath(os.path.join(root_dir, "input"))
    log_dir = os.path.abspath(os.path.join(root_dir, "log"))
    if not os.path.exists(root_dir):
        os.mkdir(root_dir)
    if not os.path.exists(input_dir):
        os.mkdir(input_dir)
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    logger = init_logger(os.path.join(log_dir, "preprocessing.log"), console_log_level)
    logging.getLogger('sqlalchemy.engine').setLevel(console_log_level)
    logger.info("Project directory: {}".format(root_dir))
    logger.debug("Input directory: {}".format(input_dir))

    # if not resume:
    #    shutil.copytree(in_dir, input_dir)
    #    rename_input_files(input_dir, logger)

    target_ids = set()
    file_id_mapping = dict()
    missing_files_type = dict()
    session = Session.get()

    # Gather target IDs
    for fn in os.listdir(input_dir):
        abs_path = os.path.join(input_dir, fn)
        doc_id = get_id(abs_path)
        target_ids.add(doc_id)
        file_id_mapping[doc_id] = abs_path

    # Get input documents for each tagger
    for tag_type in tag_types:
        result = session.query(Document).join(Tag).filter(
            Document.id.in_(target_ids),
            Document.collection == corpus,
            Tag.type == tag_type,
        ).distinct().values(Document.id)
        present_ids = set(x[0] for x in result)
        missing_ids = target_ids.difference(present_ids)
        missing_files_type[tag_type] = frozenset(file_id_mapping[x] for x in missing_ids)

    pprint.pprint(missing_files_type)
    pprint.pprint(file_id_mapping)

    # Init taggers
    kwargs = dict(collection=corpus, root_dir=root_dir, input_dir=input_dir,
                  log_dir=log_dir, config=conf, file_mapping=file_id_mapping)
    taggers = []
    if types.GENE in tag_types:
        taggers.append(GNorm(**kwargs))
    if types.DISEASE in tag_types and not use_tagger_one:
        taggers.append(DNorm(**kwargs))
    if types.CHEMICAL in tag_types and not use_tagger_one:
        taggers.append(TMChem(**kwargs))
    if types.CHEMICAL in tag_types and types.DISEASE in tag_types and use_tagger_one:
        taggers.append(TaggerOne(**kwargs))
    if types.DOSAGE_FORM in tag_types:
        taggers.append(DosageFormTagger(**kwargs))
    for tagger in taggers:
        for target_type in tagger.TYPES:
            tagger.add_files(*missing_files_type[target_type])
        tagger.prepare(resume)
    print("=== STEP 2 - Tagging ===")
    for tagger in taggers:
        tagger.start()
    for tagger in taggers:
        tagger.join()
    print("=== STEP 3 - Post-processing ===")
    for tagger in taggers:
        tagger.finalize()
    # TODO: Add clean step to expand overlapping tags
    export(output_filename, tag_types, target_ids, collection=corpus, content=True)
    print("=== Finished ===")


def main():
    parser = ArgumentParser(description="Preprocess PubMedCentral files for the use with Snorkel")

    # TODO: Fix API
    parser.add_argument("--resume", action="store_true",
                        help="Resume tagging (input: temp-directory, output: result file)")
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

    parser.add_argument("input", help="Directory with PubTator files (can be a file if --ids is set)", metavar="IN_DIR")
    parser.add_argument("output", help="Output file", metavar="OUT_FILE")
    args = parser.parse_args()

    # Create configuration wrapper
    conf = Config(args.config)

    # Perform collection and conversion
    in_dir = args.input
    if args.ids and args.corpus == "PMC":
        in_dir = tempfile.mkdtemp()
        error_file = os.path.join(in_dir, "conversion_errors.txt")
        collector = PMCCollector(conf.pmc_dir)
        files = collector.collect(args.input)
        translator = PMCTranslator()
        translator.translate_multiple(files, in_dir, error_file)

    # Add documents to database
    bulk_load(in_dir, args.corpus)

    # Create list of tagging ent types
    tag_types = types.ALL if "A" in args.tag else [TAG_TYPE_MAPPING[x] for x in args.tag]

    # TODO: Add SQL logging
    #logging.basicConfig()
    #logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    # Run actual preprocessing
    preprocess(args.corpus, in_dir, args.output, conf, *tag_types,
               resume=args.resume, console_log_level=args.loglevel.upper(),
               workdir=args.workdir, use_tagger_one=args.tagger_one)


if __name__ == "__main__":
    main()
