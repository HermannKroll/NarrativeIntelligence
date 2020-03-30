import logging
import os
import tempfile
from argparse import ArgumentParser
from typing import List

from narraint.preprocessing.convertids import load_pmcids_to_pmid_index
from narraint.preprocessing.collect import PMCCollector
from narraint.pubtator.convert import PMCConverter
from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.config import Config


def main():
    parser = ArgumentParser(description="Collect and convert PMC files from a list of pmc-ids")
    parser.add_argument("input", help="File containing PMC IDs", required=True)
    parser.add_argument("output", help="Directory to output the converted Files into")
    group_settings = parser.add_argument_group("Settings")
    group_settings.add_argument("--config", default=PREPROCESS_CONFIG,
                                help="Configuration file (default: {})".format(PREPROCESS_CONFIG))
    group_settings.add_argument("--loglevel", default="INFO")

    args = parser.parse_args()
    conf = Config(args.config)
    logging.basicConfig(level=args.loglevel.upper())

    # TODO: Logfile
    if args.output:
        out_dir = args.output
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            logging.info(f"Creating output directory {out_dir}")
    else:
        out_dir = tempfile.mkdtemp()
        logging.info(f"No output given, created temp directory at {out_dir}")

    logging.info('Load PMCID to PMID translation file')
    pmcid2pmid = load_pmcids_to_pmid_index(conf.pmcid2pmid)

    error_file = os.path.join(out_dir, "conversion_errors.txt")
    collector = PMCCollector(conf.pmc_dir)
    files = collector.collect(args.input)
    translator = PMCConverter()
    translator.convert_bulk(files, out_dir, pmcid2pmid, error_file)


if __name__ == "__main__":
    main()
