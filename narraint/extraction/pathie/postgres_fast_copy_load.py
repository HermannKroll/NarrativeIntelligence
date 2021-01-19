import argparse
import logging
from io import StringIO
from typing import List

from narraint.backend.database import Session
from narraint.extraction.openie.cleanload import PRED, clean_predications
from narraint.extraction.pathie.load_extractions import read_pathie_extractions_tsv
from narraint.extraction.versions import PATHIE_EXTRACTION


def clean_and_export_predications_to_copy_load_tsv(tuples_cleaned: List[PRED], collection, extraction_type,
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
    clean_and_export_predications_to_copy_load_tsv(predications, args.collection, extraction_type=PATHIE_EXTRACTION)
    logging.info('finished')


if __name__ == "__main__":
    main()
