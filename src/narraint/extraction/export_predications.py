import argparse
import logging
from datetime import datetime


import csv

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication
from narrant.progress import print_progress_with_eta


def export_predications_as_tsv(output_file:str, document_collection=None, export_metadata=False):
    """
    Exports the database tuples as a CSV
    :param output_file: output filename
    :param document_collection:
    :param export_metadata:
    :return: None
    """

    session = SessionExtended.get()
    logging.info('Counting predications...')
    count = Predication.query_predication_count(session, predicate_canonicalized=None,
                                                document_collection=document_collection)

    start_time = datetime.now()
    with open(output_file, 'wt') as f:
        logging.info(f'exporting {count} entries with metadata in TSV format to {output_file}...')
        writer = csv.writer(f, delimiter='\t')
        if export_metadata:
            writer.writerow(["document_id", "document_collection",
                             "subject_id", "subject_type", "subject_str",
                             "predicate", "relation",
                             "object_id", "object_type", "object_str",
                             "sentence_id", "extraction_type"])
            for idx, pred in enumerate(Predication.iterate_predications(session,
                                                                        document_collection=document_collection)):
                writer.writerow([pred.document_id, pred.document_collection,
                                 pred.subject_id, pred.subject_type, pred.subject_str,
                                 pred.predicate, pred.predicate_canonicalized,
                                 pred.object_id, pred.object_type, pred.object_str,
                                 pred.sentence_id, pred.extraction_type])
                print_progress_with_eta("exporting", idx, count, start_time)
        else:
            writer.writerow(["subject_id", "relation", "object_id"])
            logging.info(f'exporting {count} entries without metadata in TSV format to {output_file}...')
            for idx, pred in enumerate(Predication.iterate_predications(session,
                                                                        document_collection=document_collection)):
                writer.writerow([pred.subject_id, pred.predicate_canonicalized, pred.object_id])
                print_progress_with_eta("exporting", idx, count, start_time)

    logging.info('Export finished')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help='Path for the output file')
    parser.add_argument("-c", "--collection", required=False, help='Export statements only for this document collection')
    parser.add_argument("--metadata", required=False, action="store_true", help='Should metadata be exported?')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    export_predications_as_tsv(args.output, document_collection=args.collection, export_metadata=args.metadata)


if __name__ == "__main__":
    main()
