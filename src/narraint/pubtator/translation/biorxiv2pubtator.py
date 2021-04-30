import csv
import logging
from argparse import ArgumentParser
from itertools import islice
import re

from narrant.backend.models import Document

ARTIFICIL_IDS_START_AT_BIORXIV = 200000000

JATS_TITLE_REGEX = re.compile(r'<jats:title>.*?</jats:title>')
JATS_REGEX = re.compile(r'</?jats:\w+>')


def _clean_text(text):
    text_cleaned = text.replace('\n', ' ')
    text_cleaned = re.sub(JATS_TITLE_REGEX, '', text_cleaned)
    return re.sub(JATS_REGEX, '', text_cleaned)


def convert_biorxiv_articles_to_pubtator(input_file, output_file):
    """
    convert biorxiv articles (dump stems from our UB) in pubtator format
    :param input_file: a biorxiv - tab separated input file
    :param output_file: pubtator file with empty spaces for abstract if abstract is missing
    :return:
    """
    logging.info('Converting biorxiv articles to pubtator format...')
    skipped_documents = set()
    with open(input_file, 'rt', encoding='latin-1') as input_file:
        with open(output_file, 'wt', encoding='utf-8') as output_file:
            reader = csv.reader(input_file, delimiter='\t', quotechar='"', escapechar='\\')
            for idx, row in enumerate(islice(reader, 1, None)):
                doc_id = ARTIFICIL_IDS_START_AT_BIORXIV + int(row[0])
                title = _clean_text(row[2]).replace('|', ' ')
                abstract = _clean_text(row[3]).replace('|', ' ')
                if not title.strip() and not abstract.strip():
                    skipped_documents.add(doc_id)
                    continue
                if not abstract:
                    abstract = " "
                if idx > 0:
                    output_file.write('\n')
                output_file.write(Document.create_pubtator(doc_id, title, abstract))

    logging.info('The following documents have been skipped (no title and no abstract): {}'.format(skipped_documents))
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
