import logging
from argparse import ArgumentParser

import csv
from itertools import islice

from narrant.backend.models import Document


def main():
    parser = ArgumentParser(description="converts the cord19 metadata csv file...")
    parser.add_argument("input", help="CORD19 metadata csv file")
    parser.add_argument("output", help="output as a pubtator file")
    group_settings = parser.add_argument_group("Settings")
    group_settings.add_argument("--loglevel", default="INFO")

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel.upper())

    with open(args.input, 'rt') as input_file:
        with open(args.output, 'wt') as output_file:
            reader = csv.reader(input_file)
            doc_id = 1
            for row in islice(reader, 1, None):
                title, abstract = row[3].strip(), row[8].strip()
                output_file.write(Document.create_pubtator(doc_id, title, abstract))
                output_file.write('\n')
                doc_id = doc_id + 1


if __name__ == "__main__":
    main()
