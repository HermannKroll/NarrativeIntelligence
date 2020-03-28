import argparse
import logging
import os
import re

from narraint.pubtator.regex import DOCUMENT_ID


# TODO: This method should be unit-tested because its used a lot
def read_pubtator_documents(path):
    if os.path.isdir(path):
        for fn in os.listdir(path):
            if not fn.startswith(".") and fn.endswith(".txt"):
                abs_path = os.path.join(path, fn)
                yield from read_pubtator_documents(abs_path)
    else:
        content = ""
        with open(path) as f:
            for line in f:
                if line.strip():
                    content += line
                else:
                    yield content
                    content = ""
            yield content


def extract_pubtator_docs(input_file, id_file, output, logger):
    logger.info('opening id file {}...'.format(id_file))
    ids = set()
    with open(id_file, 'r') as f:
        for l in f:
            ids.add(int(l))

    logger.info('{} documents to extract...'.format(len(ids)))
    logger.info('processing input file...')
    with open(output, 'w') as f_out:
        for document_content in read_pubtator_documents(input_file):
            doc_id = DOCUMENT_ID.search(document_content)
            if doc_id in ids:
                f_out.write(document_content)

    logger.info('extraction finished')


def main():
    """

    Input: Directory with Pubtator files
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help='PubTator document collection as a single file')
    parser.add_argument("id_file", help='file including the desired ids')
    parser.add_argument("output", help='extracted documents as a single pubtator file')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logger = logging.getLogger(__name__)

    extract_pubtator_docs(args.input, args.id_file, args.output, logger)


if __name__ == "__main__":
    main()
