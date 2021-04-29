import argparse
import logging
from typing import List
from io import StringIO

from narraint.backend.database import Session
from narraint.extraction.versions import PATHIE_EXTRACTION, CORENLP_VERSION
from narraint.extraction.openie.cleanload import PRED, insert_predications_into_db, clean_predications


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


def postgres_clean_and_export_predications_to_copy_load_tsv(tuples_cleaned: List[PRED], collection, extraction_type,
                                                            clean_genes=True,
                                                            do_transform_mesh_ids_to_prefixes=True):
    """
    insert a list of cleaned tuples into the database (bulk insert)
    does not check for collisions
    :param tuples_cleaned: a list of PRED tuples
    :param collection: the document collection
    :param extraction_type: extraction type like OpenIE or PathIE
    :param clean_genes: if true the genes will be cleaned (multiple genes are split and ids are translated to symbols)
    :param do_transform_mesh_ids_to_prefixes: if true all MeSH ids will be translated to MeSH tree numbers
    :return: Nothing
    """
    predication_values, sentence_values = clean_predications(tuples_cleaned, collection, extraction_type,
                                                             clean_genes=clean_genes,
                                                             do_transform_mesh_ids_to_prefixes=do_transform_mesh_ids_to_prefixes)
    # free memory here
    tuples_cleaned.clear()
    sentence_values_len = len(sentence_values)
    predication_values_len = len(predication_values)
    logging.info(f'Exporting {len(sentence_values)} sentences to memory file')
    sent_keys = ["id", "document_id", "document_collection", "text", "md5hash"]
    f_sent = StringIO()
    for idx, sent_value in enumerate(sentence_values):
        sent_str = '{}'.format('\t'.join([str(sent_value[k]) for k in sent_keys]))
        if idx == 0:
            f_sent.write(sent_str)
        else:
            f_sent.write(f'\n{sent_str}')
    # free memory here
    sentence_values.clear()

    session = Session.get()
    connection = session.connection().connection
    cursor = connection.cursor()
    logging.info('Executing copy from sentence...')
    f_sent.seek(0)
    cursor.copy_from(f_sent, 'Sentence', sep='\t', columns=sent_keys)
    logging.info('Committing...')
    connection.commit()
    f_sent.close()

    logging.info(f'Exporting {len(predication_values)} predications to memory file')
    pred_keys = ['document_id', 'document_collection', 'subject_id', 'subject_str', 'subject_type', 'predicate',
                 'object_id', 'object_str', 'object_type', 'confidence', 'sentence_id', 'extraction_type']

    f_pred = StringIO()
    for idx, pred_val in enumerate(predication_values):
        pred_str = '{}'.format('\t'.join([str(pred_val[k]) for k in pred_keys]))
        if idx == 0:
            f_pred.write(pred_str)
        else:
            f_pred.write(f'\n{pred_str}')
    # free memory here
    predication_values.clear()

    logging.info('Executing copy from predication...')
    cursor = connection.cursor()
    f_pred.seek(0)
    cursor.copy_from(f_pred, 'Predication', sep='\t', columns=pred_keys)
    logging.info('Committing...')
    connection.commit()
    f_pred.close()
    logging.info(f'Finished {sentence_values_len} sentences and {predication_values_len} predications have been '
                 f'inserted')


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
    if Session.is_postgres:
        postgres_clean_and_export_predications_to_copy_load_tsv(predications, document_collection, extraction_type)
    else:
        insert_predications_into_db(predications, document_collection, extraction_type)
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
