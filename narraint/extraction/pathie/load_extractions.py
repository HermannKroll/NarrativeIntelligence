import argparse
import logging

from narraint.extraction.versions import PATHIE_EXTRACTION, CORENLP_VERSION
from narraint.extraction.openie.cleanload import PRED, insert_predications_into_db


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
                doc_id, e1_id, e1_str, e1_type, pred, pred_lemma, e2_id, e2_str, e2_type, sentence = line.split('\t')
                p = PRED(doc_id, "", pred, pred_lemma, "", 1.0, sentence, e1_id, e1_str, e1_type, e2_id, e2_str, e2_type)
                extractions.append(p)
                # flip triple
                p = PRED(doc_id, "", pred, pred_lemma, "", 1.0, sentence, e2_id, e2_str, e2_type, e1_id, e1_str, e1_type)
                extractions.append(p)

            except ValueError:
                tup = line.split('\t')
                logging.warning(f'skipping tuple: {tup}')
    return extractions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help='PathIE output file (created by main.py)')
    parser.add_argument("-c", "--collection", required=True, help='document collection to which the ids belong')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    logging.info('Reading extraction from tsv file...')
    predications = read_pathie_extractions_tsv(args.input)
    logging.info('{} extractions read'.format(len(predications)))
    logging.info('Inserting {} predications'.format(len(predications)))
    insert_predications_into_db(predications, args.collection, extraction_type=PATHIE_EXTRACTION)
    logging.info('finished')


if __name__ == "__main__":
    main()
