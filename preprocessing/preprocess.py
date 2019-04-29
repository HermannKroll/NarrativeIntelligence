from argparse import ArgumentParser

from preprocessing.collect import collect_files, translate_files
from preprocessing.tools import concat

PMC_DIR_DEFAULT = "/hdd2/datasets/pubmed_central"


def translate(input_filename, output, pmc_dir):
    pmc_files = collect_files(input_filename, pmc_dir)
    translate_files(pmc_files, output)


def main():
    parser = ArgumentParser(description="Preprocess PubMedCentral files for the use with Snorkel")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--translate-only", action="store_true", help="Translate PubMedCentral files to PubTator format")
    group.add_argument("--tag-only", action="store_true", help="Tag a collection of PubTator files")
    group.add_argument("--concat-only", action="store_true", help="Concat PubTator files to one single file")
    group.add_argument("--merge-only", action="store_true", help="Merge tagged PubTator files files to one single file")
    group.add_argument("--batch-only", metavar="BATCH_SIZE", type=int,
                       help="Merge PubTator files files to batches of size n")
    parser.add_argument("--pmc-dir", default=PMC_DIR_DEFAULT,
                        help="Root of the PubMedCentral files (default: {})".format(PMC_DIR_DEFAULT))
    parser.add_argument("input", help="Input file/directory", metavar="INPUT_FILE_OR_DIR")
    parser.add_argument("output", help="Output file/directory", metavar="OUTPUT_FILE_OR_DIR")
    args = parser.parse_args()

    if args.translate_only:
        translate(args.input, args.output, args.pmc_dir)
    elif args.batch_only:
        concat(args.input, args.output, args.batch_only)
    elif args.concat_only:
        concat(args.input, args.output)


if __name__ == "__main__":
    main()
