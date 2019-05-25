import logging
import os
import re
import tempfile
from argparse import ArgumentParser

from config import Config
from tagging.dnorm import DNorm
from tagging.gnorm import GNorm
from tagging.tchem import TChem
from tools import concat
from translate import collect_files, translate_files

CONFIG_DEFAULT = "config.json"
LOGGING_FORMAT = '%(asctime)s %(levelname)s %(threadName)s %(module)s:%(lineno)d %(message)s'


class NoRemainingDocumentError(Exception):
    """
    Error class indicating that no unfinished documents exist.
    """
    pass


def translate(input_filename, output, pmc_dir, translation_err_file=None):
    """
    Method takes a file with PubMedCentral IDs (PMCxxxxxx), searches ``pmc_dir`` for PubMedCentral
    XML-documents with the name
    of these ids and translates them into the PubTator Format. Results are written into ``output``.

    Documents which were not translated are listed in ``translation_err_file``.

    :param input_filename: ID file with PubMedCentral IDs
    :param output: Directory to place the translated files in PubTator format
    :param pmc_dir: Directory containing the PubMedCentral XML files
    :param translation_err_file: Filename of the list with bad documents
    """
    pmc_files = collect_files(input_filename, pmc_dir)
    translate_files(pmc_files, output, translation_err_file)


def get_next_document_id(translation_dir, tagger_one_out_dir):
    """
    Method searches the already tagged documents and returns the next document to start with.
    If no ID is found, a ValueError is raised.
    If all documents are already processed, a NoRemainingDocumentError is raised.

    :param translation_dir: Directory with the PubMedCentral PubTator documents
    :param tagger_one_out_dir: Directory with the tagged batches of TaggerOne
    :return: Next ID to work on
    :raises ValueError: if no IDs were found
    :raises NoRemainingDocumentError: if all documents are already processed
    """
    translations = sorted(fn[:-4] for fn in os.listdir(translation_dir))

    processed_files = sorted(os.listdir(tagger_one_out_dir))
    if processed_files:
        last_batch_file = processed_files[-1]
        last_batch_path = os.path.join(tagger_one_out_dir, last_batch_file)
        with open(last_batch_path) as f:
            content = f.read()
        finished_ids = re.findall(r"(\d+)\|t\|", content)
        if finished_ids:
            last_id = "PMC{}".format(finished_ids[-1])
        else:
            raise ValueError("TaggerOne result {} is empty. Please remove manually.".format(last_batch_path))
        last_idx = translations.index(last_id)
        if last_idx == len(translations) - 1:
            raise NoRemainingDocumentError
        return translations[last_idx + 1]
    else:
        return translations[0]


# def preprocess(input_file_dir_list, output_filename, conf, tag_genes=True, tag_chemicals_diseases=True, resume=False,
#                console_log_level="INFO"):
#     """
#     Method creates a full-tagged PubTator file with the documents from in ``input_file_dir_list``.
#     Method expects an ID file or an ID list if resume=False.
#     Method expects the working directory (temp-directory) of the processing to resume if resume=True.
#
#     :param console_log_level: Log level for console output
#     :param input_file_dir_list: File or list with IDs or directory with tagging to resume
#     :param output_filename: Filename of PubTator to create
#     :param conf: config object
#     :param tag_genes: flag, whether to tag genes
#     :param tag_chemicals_diseases: flag, wheter to tag chemicals and diseases
#     :param resume: flag, if method should resume (if True, tag_genes and tag_chemicals_diseases must be set accordingly)
#     """
#     print("=== STEP 1 - Preparation ===")
#     # Create paths
#     tmp_root = input_file_dir_list if resume else tempfile.mkdtemp()
#     tmp_translation = os.path.abspath(os.path.join(tmp_root, "translation"))
#     tmp_batches = os.path.abspath(os.path.join(tmp_root, "batches"))
#     tmp_tagger_out = os.path.abspath(os.path.join(tmp_root, "taggerone"))
#     tmp_gnorm_out = os.path.abspath(os.path.join(tmp_root, "gnorm"))
#     tmp_log = os.path.abspath(os.path.join(tmp_root, "log"))
#     translation_err_file = os.path.abspath(os.path.join(tmp_root, "translation_errors.txt"))
#     # Create directories
#     if not resume:
#         os.mkdir(tmp_translation)
#         os.mkdir(tmp_log)
#         if tag_chemicals_diseases:
#             os.mkdir(tmp_batches)
#             os.mkdir(tmp_tagger_out)
#         if tag_genes:
#             os.mkdir(tmp_gnorm_out)
#     # Init logger
#     formatter = logging.Formatter(LOGGING_FORMAT)
#     logger = logging.getLogger("preprocessing")
#     logger.setLevel("DEBUG")
#     fh = logging.FileHandler(os.path.join(tmp_log, "preprocessing.log"), mode="a+")
#     fh.setLevel("DEBUG")
#     fh.setFormatter(formatter)
#     ch = logging.StreamHandler()
#     ch.setLevel(console_log_level)
#     ch.setFormatter(formatter)
#     logger.addHandler(fh)
#     logger.addHandler(ch)
#     # Init resume
#     first_id = None
#     run_tagger_one = True
#     if resume and tag_chemicals_diseases:
#         try:
#             first_id = get_next_document_id(tmp_translation, tmp_tagger_out)
#             logger.debug("Resuming with document {}".format(first_id))
#         except NoRemainingDocumentError:
#             logger.debug("No document to resume with")
#             run_tagger_one = False
#     logger.info("Project directory: {}".format(tmp_root))
#     logger.debug("Translation output directory: {}".format(tmp_translation))
#     if tag_chemicals_diseases:
#         logger.debug("Batches directory: {}".format(tmp_batches))
#         logger.debug("TaggerOne output directory: {}".format(tmp_tagger_out))
#     if tag_genes:
#         logger.debug("GNormPlus output directory: {}".format(tmp_gnorm_out))
#     logger.debug("Log directory: {}".format(tmp_log))
#     if not resume:
#         translate(input_file_dir_list, tmp_translation, conf.pmc_dir, translation_err_file)
#     print("=== STEP 2 - Tagging ===")
#     thread_gnorm = Thread(target=thread_tag_genes, args=(conf, tmp_translation, tmp_gnorm_out, tmp_log),
#                           name="GNormPlus")
#     thread_taggerone = Thread(target=thread_tag_chemicals_diseases,
#                               args=(conf, tmp_translation, tmp_batches, tmp_tagger_out, tmp_log, first_id),
#                               name="TaggerOne")
#     if tag_genes:
#         thread_gnorm.start()
#     if tag_chemicals_diseases and run_tagger_one:
#         thread_taggerone.start()
#     if tag_genes:
#         thread_gnorm.join()
#     if tag_chemicals_diseases and run_tagger_one:
#         thread_taggerone.join()
#     print("=== STEP 3 - Post-processing ===")
#     genes = os.path.join(tmp_root, "G.txt")
#     chemicals = os.path.join(tmp_root, "CD.txt")
#     if tag_genes:
#         concat(tmp_gnorm_out, genes)
#     if tag_chemicals_diseases:
#         concat(tmp_tagger_out, chemicals)
#     if tag_genes and tag_chemicals_diseases:
#         merge_pubtator_files(genes, chemicals, output_filename)
#     elif tag_genes and not tag_chemicals_diseases:
#         copyfile(genes, output_filename)
#     elif not tag_genes and tag_chemicals_diseases:
#         copyfile(chemicals, output_filename)
#     print("=== Finished ===")

def preprocess(input_file_dir_list, output_filename, conf, tag_genes=True,
               tag_chemicals=True, tag_diseases=True, resume=False, console_log_level="INFO"):
    """
    Method creates a full-tagged PubTator file with the documents from in ``input_file_dir_list``.
    Method expects an ID file or an ID list if resume=False.
    Method expects the working directory (temp-directory) of the processing to resume if resume=True.

    :param console_log_level: Log level for console output
    :param input_file_dir_list: File or list with IDs or directory with tagging to resume
    :param output_filename: Filename of PubTator to create
    :param conf: config object
    :param tag_genes: flag, whether to tag genes
    :param tag_chemicals_diseases: flag, wheter to tag chemicals and diseases
    :param resume: flag, if method should resume (if True, tag_genes and tag_chemicals_diseases must be set accordingly)
    """
    print("=== STEP 1 - Preparation ===")
    # Create paths
    tmp_root = input_file_dir_list if resume else tempfile.mkdtemp()
    tmp_translation = os.path.abspath(os.path.join(tmp_root, "translation"))
    tmp_log = os.path.abspath(os.path.join(tmp_root, "log"))
    translation_err_file = os.path.abspath(os.path.join(tmp_root, "translation_errors.txt"))
    # Create directories
    if not resume:
        os.mkdir(tmp_translation)
        os.mkdir(tmp_log)
    # Init logger
    formatter = logging.Formatter(LOGGING_FORMAT)
    logger = logging.getLogger("preprocessing")
    logger.setLevel("DEBUG")
    fh = logging.FileHandler(os.path.join(tmp_log, "preprocessing.log"), mode="a+")
    fh.setLevel("DEBUG")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler()
    ch.setLevel(console_log_level)
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    # Init resume
    # first_id = None
    # run_tagger_one = True
    # if resume and tag_chemicals_diseases:
    #    try:
    #        first_id = get_next_document_id(tmp_translation, tmp_tagger_out)
    #        logger.debug("Resuming with document {}".format(first_id))
    #    except NoRemainingDocumentError:
    #        logger.debug("No document to resume with")
    #        run_tagger_one = False
    logger.info("Project directory: {}".format(tmp_root))
    logger.debug("Translation output directory: {}".format(tmp_translation))
    # if tag_chemicals_diseases:
    #    logger.debug("Batches directory: {}".format(tmp_batches))
    #    logger.debug("TaggerOne output directory: {}".format(tmp_tagger_out))
    # if tag_genes:
    #    logger.debug("GNormPlus output directory: {}".format(tmp_gnorm_out))
    # logger.debug("Log directory: {}".format(tmp_log))
    if not resume:
        translate(input_file_dir_list, tmp_translation, conf.pmc_dir, translation_err_file)
    # Init taggers
    kwargs = dict(root_dir=tmp_root, translation_dir=tmp_translation, log_dir=tmp_log, config=conf)
    gnorm = GNorm(**kwargs)
    dnorm = DNorm(**kwargs)
    tchem = TChem(**kwargs)
    if tag_genes:
        gnorm.prepare(resume)
    if tag_diseases:
        dnorm.prepare(resume)
    if tag_chemicals:
        tchem.prepare(resume)
    print("=== STEP 2 - Tagging ===")
    if tag_genes:
        gnorm.start()
    if tag_diseases:
        dnorm.start()
    if tag_chemicals:
        tchem.start()
    # Wait until finished
    if tag_genes:
        gnorm.join()
    if tag_diseases:
        dnorm.join()
    if tag_chemicals:
        tchem.join()
    print("=== STEP 3 - Post-processing ===")
    # genes = os.path.join(tmp_root, "G.txt")
    # chemicals = os.path.join(tmp_root, "CD.txt")
    # if tag_genes:
    #    concat(tmp_gnorm_out, genes)
    # if tag_chemicals_diseases:
    #    concat(tmp_tagger_out, chemicals)
    # if tag_genes and tag_chemicals_diseases:
    #    merge_pubtator_files(genes, chemicals, output_filename)
    # elif tag_genes and not tag_chemicals_diseases:
    #    copyfile(genes, output_filename)
    # elif not tag_genes and tag_chemicals_diseases:
    #    copyfile(chemicals, output_filename)
    print("=== Finished ===")


def main():
    parser = ArgumentParser(description="Preprocess PubMedCentral files for the use with Snorkel")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--translate-only", action="store_true", help="Translate PubMedCentral files to PubTator format")
    group.add_argument("--concat-only", action="store_true", help="Concat PubTator files to one single file")
    group.add_argument("--resume", action="store_true",
                       help="Resume tagging (input: temp-directory, output: result file)")

    group_tag = parser.add_argument_group()
    group_tag.add_argument("--no-genes", action="store_false", help="Do not tag genes")
    group_tag.add_argument("--no-diseases", action="store_false", help="Do not tag diseases")
    group_tag.add_argument("--no-chemicals", action="store_false", help="Do not tag chemicals")

    group_settings = parser.add_argument_group("Settings")
    group_settings.add_argument("--config", default=CONFIG_DEFAULT,
                                help="Configuration file (default: {})".format(CONFIG_DEFAULT))
    group_settings.add_argument("--loglevel", default="INFO")

    parser.add_argument("input", help="Input file/directory", metavar="INPUT_FILE_OR_DIR")
    parser.add_argument("output", help="Output file/directory", metavar="OUTPUT_FILE_OR_DIR")
    args = parser.parse_args()

    conf = Config(args.config)

    if args.translate_only:
        translate(args.input, args.output, conf.pmc_dir)
    elif args.concat_only:
        concat(args.input, args.output)
    else:
        preprocess(args.input, args.output, conf, args.no_genes, args.no_chemicals, args.no_diseases, args.resume,
                   args.loglevel.upper())


if __name__ == "__main__":
    main()
