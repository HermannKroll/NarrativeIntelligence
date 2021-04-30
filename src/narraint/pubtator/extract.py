import argparse
import logging
import os

from narrant.preprocessing.utils import get_document_id, DocumentError
from narraint.pubtator.regex import DOCUMENT_ID
from narraint.pubtator.document import TaggedDocument


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
            if content: yield content


def read_tagged_documents(path):
    for content in read_pubtator_documents(path):
        yield TaggedDocument(content)


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
            if int(doc_id.groups()[0]) in ids:
                f_out.write(document_content + "\n")

    logger.info('extraction finished')


def collect_ids_from_dir(input_dir, logger=logging):
    """
    Non-recursively collect target document ids from input_dir. Also create a mapping filepath -> id
    and the reverse mapping id -> filepath
    :param input_dir: the directory containing the pubtator files
    :param logger: optional custom logger
    :return: target_ids, mapping_file_id, mapping_id_file
    """
    mapping_id_file = dict()
    mapping_file_id = dict()
    target_ids = set()

    for fn in os.listdir(input_dir):
        abs_path = os.path.join(input_dir, fn)
        try:
            doc_id = get_document_id(abs_path)
            target_ids.add(doc_id)
            mapping_id_file[doc_id] = abs_path
            mapping_file_id[abs_path] = doc_id
        except DocumentError as e:
            logger.warning(e)
    return target_ids, mapping_file_id, mapping_id_file


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


