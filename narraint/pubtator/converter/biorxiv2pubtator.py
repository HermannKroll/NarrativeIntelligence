import csv
import logging
from argparse import ArgumentParser
from itertools import islice
import re

from narraint.backend.models import Document

ARTIFICIL_IDS_START_AT_BIORXIV = 200000000

JATS_REGEX = re.compile(r'</?jats:\w+>')


def _clean_text(text):
    return re.sub(JATS_REGEX, '', text.replace('\n', ' '))


def convert_biorxiv_articles_to_pubtator(input_file, output_file):
    """
    convert biorxiv articles (dump stems from our UB) in pubtator format
    :param input_file: a biorxiv - tab separated input file
    :param output_file: pubtator file with empty spaces for abstract if abstract is missing
    :return:
    """
    logging.info('Converting biorxiv articles to pubtator format...')
    with open(input_file, 'rt', encoding='latin-1') as input_file:
        with open(output_file, 'wt') as output_file:
            reader = csv.reader(input_file, delimiter='\t', quotechar='"', escapechar='\\')
            for idx, row in enumerate(islice(reader, 1, None)):
                doc_id = ARTIFICIL_IDS_START_AT_BIORXIV + int(row[0])
                title = _clean_text(row[2])
                abstract = _clean_text(row[3])
                if not abstract:
                    abstract = " "
                if idx > 0:
                    output_file.write('\n')
                output_file.write(Document.create_pubtator(doc_id, title, abstract))

    logging.info('{} documents written in PubTator format'.format(doc_id-ARTIFICIL_IDS_START_AT_BIORXIV))


def main():
    parser = ArgumentParser()
    parser.add_argument("input", help="biorxiv tab separated file", metavar="FILE")
    parser.add_argument("output", help="Output will be written in PubTator Format", metavar="FILE")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    convert_biorxiv_articles_to_pubtator(args.input, args.output)


if __name__ == "__main__":
    main()
