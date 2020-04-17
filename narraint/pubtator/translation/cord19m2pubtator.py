import logging
import os
import tempfile
from argparse import ArgumentParser

from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.config import Config
from narraint.preprocessing.convertids import load_pmcids_to_pmid_index
from narraint.pubtator.translation.csv2pubtator import CsvConverter


def main():
    parser = ArgumentParser(description="Collect and convert PMC files from a list of pmc-ids")
    parser.add_argument("input", help="File containing PMC IDs OR directory containing PMC files")
    parser.add_argument("output", help="Directory to output the converted Files into")
    group_settings = parser.add_argument_group("Settings")
    group_settings.add_argument("--config", default=PREPROCESS_CONFIG,
                                help="Configuration file (default: {})".format(PREPROCESS_CONFIG))
    group_settings.add_argument("--loglevel", default="INFO")

    args = parser.parse_args()
    conf = Config(args.config)
    logging.basicConfig(level=args.loglevel.upper())
    logging.info('Load PMCID to PMID translation file')
    pmcid2pmid = load_pmcids_to_pmid_index(conf.pmcid2pmid)
    translator = CsvConverter(primary_index=0, id_index=6, title_index=3, abstract_index=8, pmc_index=5, pmcids2pmids=pmcid2pmid)
    translator.convert(args.input, args.output)


if __name__ == "__main__":
    main()
