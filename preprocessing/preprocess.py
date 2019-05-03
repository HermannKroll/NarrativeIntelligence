import os
import tempfile
from argparse import ArgumentParser
from threading import Thread

from preprocessing.collect import collect_files, translate_files
from preprocessing.config import Config
from preprocessing.tag import tag_genes, tag_chemicals_diseases
from preprocessing.tools import concat, merge_pubtator_files

CONFIG_DEFAULT = "config.json"


def translate(input_filename, output, pmc_dir, translation_err_file=None):
    pmc_files = collect_files(input_filename, pmc_dir)
    translate_files(pmc_files, output, translation_err_file)


def main():
    parser = ArgumentParser(description="Preprocess PubMedCentral files for the use with Snorkel")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--translate-only", action="store_true", help="Translate PubMedCentral files to PubTator format")
    group.add_argument("--tag-only", action="store_true", help="Tag a collection of PubTator files")
    group.add_argument("--concat-only", action="store_true", help="Concat PubTator files to one single file")
    group.add_argument("--merge-only", action="store_true", help="Merge tagged PubTator files files to one single file")
    group.add_argument("--batch-only", metavar="BATCH_SIZE", type=int,
                       help="Merge PubTator files files to batches of size n")
    group2 = parser.add_argument_group("Settings")
    group2.add_argument("--config", default=CONFIG_DEFAULT,
                        help="Configuration file (default: {})".format(CONFIG_DEFAULT))
    parser.add_argument("input", help="Input file/directory", metavar="INPUT_FILE_OR_DIR")
    parser.add_argument("output", help="Output file/directory", metavar="OUTPUT_FILE_OR_DIR")
    args = parser.parse_args()

    conf = Config(args.config)

    if args.translate_only:
        translate(args.input, args.output, conf.pmc_dir)
    elif args.batch_only:
        concat(args.input, args.output, args.batch_only)
    elif args.concat_only:
        concat(args.input, args.output)
    else:
        print("=== STEP 1 - Preparation ===")
        tmp_root = tempfile.mkdtemp()
        tmp_translation = os.path.join(tmp_root, "translation")
        tmp_batches = os.path.join(tmp_root, "batches")
        tmp_tagger_out = os.path.join(tmp_root, "taggerone")
        tmp_gnorm_out = os.path.join(tmp_root, "gnorm")
        tmp_log = os.path.join(tmp_root, "log")
        os.mkdir(tmp_translation)
        os.mkdir(tmp_batches)
        os.mkdir(tmp_tagger_out)
        os.mkdir(tmp_gnorm_out)
        os.mkdir(tmp_log)
        translation_err_file = os.path.join(tmp_root, "translation_errors.txt")
        print("INFO: Temp directory: {}".format(tmp_root))
        print("DEBUG: Translation output directory: {}".format(tmp_translation))
        print("DEBUG: Batches directory: {}".format(tmp_batches))
        print("DEBUG: TaggerOne output directory: {}".format(tmp_tagger_out))
        print("DEBUG: GNormPlus output directory: {}".format(tmp_gnorm_out))
        print("DEBUG: Log directory: {}".format(tmp_log))
        translate(args.input, tmp_translation, conf.pmc_dir, translation_err_file)
        concat(tmp_translation, os.path.join(tmp_batches, "batch.txt"), conf.tagger_one_batch_size)
        print("=== STEP 2 - Tagging ===")
        thread_gnorm = Thread(target=tag_genes, args=(conf, tmp_translation, tmp_gnorm_out, tmp_log))
        thread_taggerone = Thread(target=tag_chemicals_diseases, args=(conf, tmp_batches, tmp_tagger_out, tmp_log))
        thread_gnorm.start()
        thread_taggerone.start()
        thread_gnorm.join()
        thread_taggerone.join()
        print("=== STEP 3 - Post-processing ===")
        genes = os.path.join(tmp_root, "G.txt")
        chemicals = os.path.join(tmp_root, "CD.txt")
        concat(tmp_gnorm_out, genes)
        concat(tmp_tagger_out, chemicals)
        merge_pubtator_files(genes, chemicals, args.output)
        print("=== Finished ===")


if __name__ == "__main__":
    main()
