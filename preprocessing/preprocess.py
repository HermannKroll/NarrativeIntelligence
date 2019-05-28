import logging
import os
import tempfile
from argparse import ArgumentParser

from config import Config
from tagging.base import merge_result_files
from tagging.dnorm import DNorm
from tagging.gnorm import GNorm
from tagging.tmchem import TMChem
from tools import concat
from translate import collect_files, translate_files

CONFIG_DEFAULT = "config.json"
LOGGING_FORMAT = '%(asctime)s %(levelname)s %(threadName)s %(module)s:%(lineno)d %(message)s'


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


def preprocess(input_file_dir_list, output_filename, conf, tag_genes=True,
               tag_chemicals=True, tag_diseases=True, resume=False, console_log_level="INFO", workdir=None):
    """
    Method creates a full-tagged PubTator file with the documents from in ``input_file_dir_list``.
    Method expects an ID file or an ID list if resume=False.
    Method expects the working directory (temp-directory) of the processing to resume if resume=True.

    :param workdir: Working directory
    :param console_log_level: Log level for console output
    :param input_file_dir_list: File or list with IDs or directory with tagging to resume
    :param output_filename: Filename of PubTator to create
    :param conf: config object
    :param tag_genes: flag, whether to tag genes
    :param tag_chemicals: flag, wheter to tag chemicals
    :param tag_diseases: flag, wheter to tag diseases
    :param resume: flag, if method should resume (if True, tag_genes, tag_chemicals and tag_diseases must
    be set accordingly)
    """
    print("=== STEP 1 - Preparation ===")
    # Create paths
    tmp_root = input_file_dir_list if resume else (os.path.abspath(workdir) if workdir else tempfile.mkdtemp())
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
    logger.info("Project directory: {}".format(tmp_root))
    logger.debug("Translation output directory: {}".format(tmp_translation))
    if not resume:
        translate(input_file_dir_list, tmp_translation, conf.pmc_dir, translation_err_file)
    # Init taggers
    kwargs = dict(root_dir=tmp_root, translation_dir=tmp_translation, log_dir=tmp_log, config=conf)
    gene_tagger = GNorm(**kwargs)
    disease_tagger = DNorm(**kwargs)
    chemical_tagger = TMChem(**kwargs)
    if tag_genes:
        gene_tagger.prepare(resume)
    if tag_diseases:
        disease_tagger.prepare(resume)
    if tag_chemicals:
        chemical_tagger.prepare(resume)
    print("=== STEP 2 - Tagging ===")
    if tag_genes:
        gene_tagger.start()
    if tag_diseases:
        disease_tagger.start()
    if tag_chemicals:
        chemical_tagger.start()
    # Wait until finished
    if tag_genes:
        gene_tagger.join()
    if tag_diseases:
        disease_tagger.join()
    if tag_chemicals:
        chemical_tagger.join()
    print("=== STEP 3 - Post-processing ===")
    result_files = []
    if tag_genes:
        gene_tagger.finalize()
        result_files.append(gene_tagger.result_file)
    if tag_diseases:
        disease_tagger.finalize()
        result_files.append(disease_tagger.result_file)
    if tag_chemicals:
        chemical_tagger.finalize()
        result_files.append(chemical_tagger.result_file)
    merge_result_files(tmp_translation, output_filename, *result_files)
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
    group_settings.add_argument("--workdir", default=None)

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
                   args.loglevel.upper(), workdir=args.workdir)


if __name__ == "__main__":
    main()
