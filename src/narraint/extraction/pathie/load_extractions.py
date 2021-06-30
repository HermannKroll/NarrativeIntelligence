import argparse
import logging

from narraint.extraction.loading.cleanload import PRED, clean_and_load_predications_into_db
from narraint.extraction.versions import PATHIE_EXTRACTION


def read_pathie_extractions_tsv(pathie_tsv_file: str):
    """
    Reads data from a PathIE output file (created by main.py)
    :param pathie_tsv_file: PathIE output (is a tsv file)
    :return: a list of PRED tuples
    """
    extractions = []
    with open(pathie_tsv_file, 'rt') as f:
        for line in f:
            try:
                doc_id, e1_id, e1_str, e1_type, pred, pred_lemma, e2_id, e2_str, e2_type, conf, sentence = line.split(
                    '\t')
                p = PRED(doc_id, "", pred, pred_lemma, "", conf, sentence, e1_id, e1_str, e1_type, e2_id, e2_str,
                         e2_type)
                extractions.append(p)
                # flip triple
            #  p = PRED(doc_id, "", pred, pred_lemma, "", 1.0, sentence, e2_id, e2_str, e2_type, e1_id, e1_str, e1_type)
            # extractions.append(p)

            except ValueError:
                tup = line.split('\t')
                logging.warning(f'skipping tuple: {tup}')
    return extractions


def load_pathie_extractions(pathie_tsv_file: str, document_collection, extraction_type):
    """
    Wrapper to load PathIE extractions into the database
    uses fast mode if postgres connection
    fallback: slower insertion
    :param pathie_tsv_file: PathIE tsv file extraction path
    :param document_collection: the document collection
    :param extraction_type: PathIE extraction type
    :return:
    """
    logging.info(f'Reading extraction from {pathie_tsv_file}...')
    predications = read_pathie_extractions_tsv(pathie_tsv_file)
    logging.info('{} extractions read'.format(len(predications)))
    logging.info('Inserting {} predications'.format(len(predications)))
    clean_and_load_predications_into_db(predications, document_collection, extraction_type)
    logging.info('finished')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help='PathIE output file (created by main.py)')
    parser.add_argument("-c", "--collection", required=True, help='document collection to which the ids belong')
    parser.add_argument("-et", "--extraction_type", help="PathIE|PathIEStanza", default=PATHIE_EXTRACTION)

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    load_pathie_extractions(args.input, args.collection, args.extraction_type)


if __name__ == "__main__":
    main()
