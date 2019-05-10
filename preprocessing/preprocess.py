import os
import re
import tempfile
from argparse import ArgumentParser
from shutil import copyfile
from threading import Thread

from preprocessing.collect import collect_files, translate_files
from preprocessing.config import Config
from preprocessing.tag import thread_tag_chemicals_diseases, thread_tag_genes
from preprocessing.tools import concat, merge_pubtator_files

CONFIG_DEFAULT = "config.json"


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


def preprocess(input_file_dir_list, output_filename, conf, tag_genes=True, tag_chemicals_diseases=True, resume=False):
    """
    Method creates a full-tagged PubTator file with the documents from in ``input_file_dir_list``.
    Method expects an ID file or an ID list if resume=False.
    Method expects the working directory (temp-directory) of the processing to resume if resume=True.

    :param input_file_dir_list: File or list with IDs or directory with tagging to resume
    :param output_filename: Filename of PubTator to create
    :param conf: config object
    :param tag_genes: flag, whether to tag genes
    :param tag_chemicals_diseases: flag, wheter to tag chemicals and diseases
    :param resume: flag, if method should resume (if True, tag_genes and tag_chemicals_diseases must be set accordingly)
    """
    print("=== STEP 1 - Preparation ===")
    tmp_root = input_file_dir_list if resume else tempfile.mkdtemp()
    tmp_translation = os.path.join(tmp_root, "translation")
    tmp_batches = os.path.join(tmp_root, "batches")
    tmp_tagger_out = os.path.join(tmp_root, "taggerone")
    tmp_gnorm_out = os.path.join(tmp_root, "gnorm")
    tmp_log = os.path.join(tmp_root, "log")
    if not resume:
        os.mkdir(tmp_translation)
        os.mkdir(tmp_log)
        if tag_chemicals_diseases:
            os.mkdir(tmp_batches)
            os.mkdir(tmp_tagger_out)
        if tag_genes:
            os.mkdir(tmp_gnorm_out)
    translation_err_file = os.path.join(tmp_root, "translation_errors.txt")
    first_id = None
    run_tagger_one = True
    if resume:
        try:
            first_id = get_next_document_id(tmp_translation, tmp_tagger_out)
            print("DEBUG: Resuming with document {}".format(first_id))
        except NoRemainingDocumentError:
            print("DEBUG: No document to resume with")
            run_tagger_one = False
    print("INFO: Temp directory: {}".format(tmp_root))
    print("DEBUG: Translation output directory: {}".format(tmp_translation))
    if tag_chemicals_diseases:
        print("DEBUG: Batches directory: {}".format(tmp_batches))
        print("DEBUG: TaggerOne output directory: {}".format(tmp_tagger_out))
    if tag_genes:
        print("DEBUG: GNormPlus output directory: {}".format(tmp_gnorm_out))
    print("DEBUG: Log directory: {}".format(tmp_log))
    if not resume:
        translate(input_file_dir_list, tmp_translation, conf.pmc_dir, translation_err_file)
    print("=== STEP 2 - Tagging ===")
    thread_gnorm = Thread(target=thread_tag_genes, args=(conf, tmp_translation, tmp_gnorm_out, tmp_log))
    thread_taggerone = Thread(target=thread_tag_chemicals_diseases,
                              args=(conf, tmp_translation, tmp_batches, tmp_tagger_out, tmp_log, first_id))
    if tag_genes:
        thread_gnorm.start()
    if tag_chemicals_diseases and run_tagger_one:
        thread_taggerone.start()
    if tag_genes:
        thread_gnorm.join()
    if tag_chemicals_diseases and run_tagger_one:
        thread_taggerone.join()
    print("=== STEP 3 - Post-processing ===")
    genes = os.path.join(tmp_root, "G.txt")
    chemicals = os.path.join(tmp_root, "CD.txt")
    if tag_genes:
        concat(tmp_gnorm_out, genes)
    if tag_chemicals_diseases:
        concat(tmp_tagger_out, chemicals)
    if tag_genes and tag_chemicals_diseases:
        merge_pubtator_files(genes, chemicals, output_filename)
    elif tag_genes and not tag_chemicals_diseases:
        copyfile(genes, output_filename)
    elif not tag_genes and tag_chemicals_diseases:
        copyfile(chemicals, output_filename)
    print("=== Finished ===")


def main():
    parser = ArgumentParser(description="Preprocess PubMedCentral files for the use with Snorkel")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--translate-only", action="store_true", help="Translate PubMedCentral files to PubTator format")
    group.add_argument("--concat-only", action="store_true", help="Concat PubTator files to one single file")
    group.add_argument("--resume", action="store_true",
                       help="Resume tagging (input: temp-directory, output: result file)")

    group_tag = parser.add_mutually_exclusive_group()
    group_tag.add_argument("--no-genes", action="store_false", help="Do not tag genes")
    group_tag.add_argument("--no-cd", action="store_false", help="Do not tag chemicals and diseases")

    group_settings = parser.add_argument_group("Settings")
    group_settings.add_argument("--config", default=CONFIG_DEFAULT,
                                help="Configuration file (default: {})".format(CONFIG_DEFAULT))

    parser.add_argument("input", help="Input file/directory", metavar="INPUT_FILE_OR_DIR")
    parser.add_argument("output", help="Output file/directory", metavar="OUTPUT_FILE_OR_DIR")
    args = parser.parse_args()

    conf = Config(args.config)

    if args.translate_only:
        translate(args.input, args.output, conf.pmc_dir)
    elif args.concat_only:
        concat(args.input, args.output)
    else:
        preprocess(args.input, args.output, conf, args.no_genes, args.no_cd, args.resume)


if __name__ == "__main__":
    main()
