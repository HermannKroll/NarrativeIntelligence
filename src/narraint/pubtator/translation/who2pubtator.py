import csv
import logging
from argparse import ArgumentParser
from itertools import islice

from narrant.backend.models import Document

ARTIFICIL_IDS_START_AT = 100000000


def convert_who_covid19_article_database_to_pubtator(input_file, output_file):
    """
    Converts the WHO article database to putator format
    Database Information are available at:
    https://www.who.int/emergencies/diseases/novel-coronavirus-2019/global-research-on-novel-coronavirus-2019-ncov
    :param input_file: the who database file
    :param output_file: pubtator file with empty spaces for abstract if abstract is missing
    :return:
    """
    logging.info('Converting WHO COVID19 Article database to pubtator format...')
    skipped_documents = set()
    with open(input_file, 'rt') as input_file:
        with open(output_file, 'wt') as output_file:
            reader = csv.reader(input_file)
            for idx, row in enumerate(islice(reader, 1, None)):
                doc_id = ARTIFICIL_IDS_START_AT + idx
                title = row[0].replace('|', ' ')
                abstract = row[2].replace('|', ' ')
                if not title.strip() and not abstract.strip():
                    skipped_documents.add(doc_id)
                    continue
                if not abstract:
                    abstract = " "
                if idx > 0:
                    output_file.write('\n')
                output_file.write(Document.create_pubtator(doc_id, title, abstract))

    logging.info('The following documents have been skipped (no title and no abstract): {}'.format(skipped_documents))
    logging.info('{} documents written in PubTator format'.format(doc_id-ARTIFICIL_IDS_START_AT))


def main():
    parser = ArgumentParser()
    parser.add_argument("input", help="WHO COVID19 database file", metavar="FILE")
    parser.add_argument("output", help="Output will be written in PubTator Format", metavar="FILE")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    convert_who_covid19_article_database_to_pubtator(args.input, args.output)


if __name__ == "__main__":
    main()
