import argparse
import logging

from narraint.opendependencyextraction.main import PATH_EXTRACTION, CORENLP_VERSION
from narraint.openie.cleanload import PRED, insert_predications_into_db


def read_extractions_tsv(tsv_file):
    extractions = []
    with open(tsv_file, 'rt') as f:
        for line in f:
            doc_id, e1_id, e1_str, e1_type, pred, pred_lemma, e2_id, e2_str, e2_type, sentence = line.split('\t')
            extractions.append((doc_id, e1_id, e1_str, e1_type, pred, pred_lemma,  e2_id, e2_str, e2_type, sentence))
    return extractions


def main():
    """
    Input: Directory with Pubtator files
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help='Extraction TSV file')
    parser.add_argument("-c", "--collection", required=True, help='collection to which the ids belong')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    logging.info('Reading extraction from tsv file...')
    extractions = read_extractions_tsv(args.input)
    logging.info('{} extractions read'.format(len(extractions)))
    predications = []
    logging.info('Converting to predications...')
    for doc_id, e1_id, e1_str, e1_type, pred, pred_lemma,  e2_id, e2_str, e2_type, sentence in extractions:
        pred = PRED(doc_id, "", pred, pred_lemma, "", 1.0, sentence, e1_id, e1_str, e1_type, e2_id, e2_str, e2_type)
        predications.append(pred)
    logging.info('Inserting {} predications'.format(len(predications)))
    insert_predications_into_db(predications, args.collection, extraction_type=PATH_EXTRACTION,
                                version=CORENLP_VERSION)
    logging.info('finished')


if __name__ == "__main__":
    main()
