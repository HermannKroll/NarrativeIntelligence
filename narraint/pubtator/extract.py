import argparse
import logging
import re

REGEX_TITLE_OR_ABSTRACT = re.compile("(\d+)\|[at]\|(.*?)\n")


# TODO: Replace by collector class
def extract_pubtator_docs(collection_dir, id_file, output, logger):
    logger.info('opening id file {}...'.format(id_file))
    ids = set()
    with open(id_file, 'r') as f:
        for l in f:
            ids.add(int(l))

    logger.info('{} documents to extract...'.format(len(ids)))
    logger.info('processing input file...')
    with open(collection_dir, 'r') as f:
        with open(output, 'w') as f_out:
            doc_id = -1
            doc_lines = []
            first_doc = True
            for line in f:
                # skip empty line
                if line == '\n':
                    if len(doc_lines) > 0 and doc_id != -1:
                        if doc_id in ids:
                            f_out.write(''.join(doc_lines))
                            first_doc = False
                        doc_lines = []
                        doc_id = -1
                    continue
                # add an empty line before each new document
                if doc_id == -1 and not first_doc:
                    doc_lines.append('\n')

                if REGEX_TITLE_OR_ABSTRACT.match(line):
                    doc_id = int(line.split('|')[0])
                doc_lines.append(line)

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
