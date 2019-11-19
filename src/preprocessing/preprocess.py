import logging
import os
import re
import shutil
import tempfile
from argparse import ArgumentParser

from config import PREPROCESS_CONFIG
from preprocessing.config import Config
from preprocessing.tagging.base import merge_result_files
from preprocessing.tagging.dnorm import DNorm
from preprocessing.tagging.dosage import DosageFormTagger
from preprocessing.tagging.gnorm import GNorm
from preprocessing.tagging.taggerone import TaggerOne
from preprocessing.tagging.tmchem import TMChem
from preprocessing.translate import PMCCollector, PMCTranslator

LOGGING_FORMAT = '%(asctime)s %(levelname)s %(threadName)s %(module)s:%(lineno)d %(message)s'


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


def preprocess(input_file_dir_list, output_filename, conf,
               tag_chemicals=False, tag_diseases=False, tag_dosage_forms=False, tag_genes=False,
               resume=False, console_log_level="INFO", workdir=None, skip_translation=False, use_tagger_one=False):
    """
    Method creates a full-tagged PubTator file with the documents from in ``input_file_dir_list``.
    Method expects an ID file or an ID list if resume=False.
    Method expects the working directory (temp-directory) of the processing to resume if resume=True.

    :param use_tagger_one:
    :param tag_dosage_forms: flat, whether to tag dosage forms
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
    :param skip_translation: Flag whether to skip the translation/collection of files. `input_file_dir_list` is a
        directory with PubTator files to process.
    """
    print("=== STEP 1 - Preparation ===")
    # Create paths
    tmp_root = input_file_dir_list if resume else (os.path.abspath(workdir) if workdir else tempfile.mkdtemp())
    if not os.path.exists(tmp_root):
        os.mkdir(tmp_root)
    tmp_translation = os.path.abspath(os.path.join(tmp_root, "translation"))
    tmp_log = os.path.abspath(os.path.join(tmp_root, "log"))
    translation_err_file = os.path.abspath(os.path.join(tmp_root, "translation_errors.txt"))
    # Create directories
    if not resume:
        if not skip_translation:
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
        if skip_translation:
            shutil.copytree(input_file_dir_list, tmp_translation)
            rename_input_files(tmp_translation, logger)
        else:
            collector = PMCCollector(conf.pmc_dir)
            files = collector.collect(input_file_dir_list)
            translator = PMCTranslator()
            translator.translate_multiple(files, tmp_translation, translation_err_file)
    # Init taggers
    kwargs = dict(root_dir=tmp_root, translation_dir=tmp_translation, log_dir=tmp_log, config=conf)
    taggers = []
    if tag_genes:
        t = GNorm(**kwargs)
        taggers.append(t)
    if tag_diseases and not use_tagger_one:
        t = DNorm(**kwargs)
        taggers.append(t)
    if tag_chemicals and not use_tagger_one:
        t = TMChem(**kwargs)
        taggers.append(t)
    if tag_chemicals and tag_diseases and use_tagger_one:
        t = TaggerOne(**kwargs)
        taggers.append(t)
    if tag_dosage_forms:
        t = DosageFormTagger(**kwargs)
        taggers.append(t)
    for tagger in taggers:
        tagger.prepare(resume)
    print("=== STEP 2 - Tagging ===")
    for tagger in taggers:
        tagger.start()
    for tagger in taggers:
        tagger.join()
    print("=== STEP 3 - Post-processing ===")
    result_files = []
    for tagger in taggers:
        tagger.finalize()
        result_files.append(tagger.result_file)
    # TODO: Add clean step to expand overlapping tags
    merge_result_files(tmp_translation, output_filename, *result_files)
    print("=== Finished ===")


def main():
    parser = ArgumentParser(description="Preprocess PubMedCentral files for the use with Snorkel")

    parser.add_argument("--resume", action="store_true",
                        help="Resume tagging (input: temp-directory, output: result file)")
    parser.add_argument("--skip-translation", action="store_true",
                        help="Skip translation. INPUT is the directory with PubTator files to tag.")

    group_tag = parser.add_argument_group("Tagging")
    group_tag.add_argument("-G", "--gene", action="store_true", help="Tag genes")
    group_tag.add_argument("-D", "--disease", action="store_true", help="Tag diseases")
    group_tag.add_argument("-C", "--chemical", action="store_true", help="Tag chemicals")
    group_tag.add_argument("-F", "--dosage", action="store_true", help="Tag dosage forms")
    group_tag.add_argument("--tagger-one", action="store_true",
                           help="Tag diseases and chemicals with TaggerOne instead of DNorm and tmChem.")

    group_settings = parser.add_argument_group("Settings")
    group_settings.add_argument("--config", default=PREPROCESS_CONFIG,
                                help="Configuration file (default: {})".format(PREPROCESS_CONFIG))
    group_settings.add_argument("--loglevel", default="INFO")
    group_settings.add_argument("--workdir", default=None)

    parser.add_argument("input", help="ID file / Workdir / Directory with PMC files", metavar="INPUT_FILE_OR_DIR")
    parser.add_argument("output", help="Output file/directory", metavar="OUTPUT_FILE_OR_DIR")
    args = parser.parse_args()

    conf = Config(args.config)

    preprocess(args.input, args.output, conf,
               args.chemical, args.disease, args.dosage, args.gene,
               resume=args.resume, console_log_level=args.loglevel.upper(), workdir=args.workdir,
               skip_translation=args.skip_translation, use_tagger_one=args.tagger_one)


if __name__ == "__main__":
    main()
