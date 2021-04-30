import os
import re
import sys

import logging
from argparse import ArgumentParser
from narrant.backend.models import Document



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
        logging.info("Reading file ...")
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
                content = Document.create_pubtator(did,title,abstract_by_id[did])
                with open(out_fn, "w") as f:
                    f.write(content + '\n')
            else:
                logging.info("WARNING: Document {} has no abstract".format(did))
            current_percentage = int((count + 1.0) / total * 100.0)
            if current_percentage > last_percentage:
                sys.stdout.write("\rWriting {}/{} patents ... {} %".format(count + 1, total,
                                                                           current_percentage))
                last_percentage = current_percentage
            count += 1
        logging.info(" done")

def main():
    parser = ArgumentParser(description="Tool to convert Patent file to Pubtator format")
    parser.add_argument("input", help="Input file", metavar="INPUT_FILE_OR_DIR")
    parser.add_argument("output", help="Output file/directory", metavar="OUTPUT_FILE_OR_DIR")
    args=parser.parse_args()

    t = PatentConverter()
    t.convert(args.input, args.output)

if __name__ == "__main__":
    main()