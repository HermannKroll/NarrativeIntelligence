"""
Module creates a single text file in the Pubtator format with the full text documents from list of PMCIDs and the
PubMedCentral Open Access Document collection.

*Which PubMedCentral files are collected?*

The module collects all PubMedCentral files with a user-specified ID.

This set of documents is scanned for text, contained in a p-Node, which is child of a sec-Node.
Some documents do not follow this schema (e.g., PMC3153655, which is a schedule for the SNIP conference).

"""
import os
import re
import sys

import logging
from argparse import ArgumentParser
from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.collect import PMCCollector
from narraint.preprocessing.config import Config
from narraint.preprocessing.convertids import load_pmcids_to_pmid_index
from narraint.pubtator.translation.pmc import PMCConverter

FMT_EPA_TTL = "TIB-EPA"
FMT_PMC_XML = "PMC-XML"
FMT_CHOICES = (
    FMT_EPA_TTL,
    FMT_PMC_XML,
)


class PatentConverter:
    """
    Convert TIB patents dump to collection of PubTator documents.

    .. note:

       Patents are identified using a country code and an ID, which are only unique in combination. Since PubTator
       IDs need to be digits, we replace the country code with a unique digit.
    """
    REGEX_ID = re.compile(r"^\d+$")
    COUNTRIES = {"AU", "CN", "WO", "GB", "US", "EP", "CA"}
    COUNTY_PREFIX = dict(
        AU=1,
        CN=2,
        WO=3,
        GB=4,
        US=5,
        EP=6,
        CA=7,
    )
    COUNTY_PREFIX_REVERS = ["AU", "CN", "WO", "GB", "US", "EP", "CA"]

    @staticmethod
    def decode_patent_country_code(patent_id):
        patent_str = str(patent_id)
        c_code, rest = int(patent_str[0]), patent_str[1:]
        if c_code == 0 or c_code > len(PatentConverter.COUNTY_PREFIX_REVERS):
            raise ValueError('Country Code {} is unknown'.format(c_code))
        return PatentConverter.COUNTY_PREFIX_REVERS[c_code-1] + rest

    def convert(self, in_file, out_dir):
        """
        `in_file` is the file preprocessed by the Academic library of the TU Braunschweig.

        :param in_file: File for the TIB dump
        :param out_dir: Directory with PubTator files for TIB
        :return:
        """
        if not os.path.exists(out_dir):
            os.mkdir(out_dir)
        print("Reading file ...")
        title_by_id = dict()
        abstract_by_id = dict()
        count = 0
        with open(in_file) as f:
            for idx, line in enumerate(f):
                id_part, body = line.strip().split("|", maxsplit=1)
                did = id_part[id_part.rindex(":") + 1:]
                country_code = did[:2]
                patent_id = did[2:]
                if country_code in self.COUNTRIES and self.REGEX_ID.fullmatch(patent_id):
                    count += 1
                    did = "{}{}".format(self.COUNTY_PREFIX[country_code], patent_id)
                    if idx % 2 == 0:
                        title_by_id[did] = body.title()
                    else:
                        abstract_by_id[did] = body

        sys.stdout.write("Writing {}/{} patents ...".format(int(count / 2), int((idx + 1) / 2)))
        total = len(title_by_id.keys())
        count = 0
        last_percentage = 0
        for did, title in title_by_id.items():
            if did in abstract_by_id:
                out_fn = os.path.join(out_dir, "{}.txt".format(did))
                with open(out_fn, "w") as f:
                    f.write("{}|t|{}\n".format(did, title))
                    f.write("{}|a|{}\n\n".format(did, abstract_by_id[did]))
            else:
                print("WARNING: Document {} has no abstract".format(did))
            current_percentage = int((count + 1.0) / total * 100.0)
            if current_percentage > last_percentage:
                sys.stdout.write("\rWriting {}/{} patents ... {} %".format(count + 1, total,
                                                                           current_percentage))
                last_percentage = current_percentage
            count += 1
        print(" done")


def main():
    parser = ArgumentParser(description="Tool to convert PubMedCentral XML files/Patent files to Pubtator format")

    parser.add_argument("-c", "--collect", metavar="DIR", help="Collect PubMedCentral files from DIR")
    parser.add_argument("-f", "--format", help="Format of input files", default=FMT_PMC_XML,
                        choices=FMT_CHOICES)
    parser.add_argument("--config", default=PREPROCESS_CONFIG,
                        help="Configuration file (default: {})".format(PREPROCESS_CONFIG))

    parser.add_argument("input", help="Input file/directory", metavar="INPUT_FILE_OR_DIR")
    parser.add_argument("output", help="Output file/directory", metavar="OUTPUT_FILE_OR_DIR")
    args = parser.parse_args()

    if args.format == FMT_PMC_XML:
        t = PMCConverter()
        # Create configuration wrapper
        conf = Config(args.config)

        logging.info('loading pmcid to pmid translation file...')
        pmcid2pmid = load_pmcids_to_pmid_index(conf.pmcid2pmid)

        if args.collect:
            collector = PMCCollector(args.collect)
            files = collector.collect(args.input)
            t.convert_bulk(files, args.output, pmcid2pmid)
        else:
            if os.path.isdir(args.input):
                files = [os.path.join(args.input, fn) for fn in os.listdir(args.input) if fn.endswith(".nxml")]
                t.convert_bulk(files, args.output, pmcid2pmid)
            else:
                t.convert(args.input, args.output)

    if args.format == FMT_EPA_TTL:
        if args.collect:
            print("WARNING: Ignoring --collect")
        t = PatentConverter()
        t.convert(args.input, args.output)


if __name__ == "__main__":
    main()
