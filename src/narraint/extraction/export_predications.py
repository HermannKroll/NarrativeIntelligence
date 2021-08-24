import argparse
import logging
from datetime import datetime
import typing as tp
import pathlib as pl

import csv

import rdflib

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication
from narrant.progress import print_progress_with_eta, Progress


def export_predications_as_rdf(output_file: tp.Union[pl.Path, str], document_collection=None):
    """
    Exports predications in a turtle rdf serialization format
    :param output_file: the path to the output file
    :param document_collection: export statements for this document collection only (optional)
    :return: None
    """
    session = SessionExtended.get()
    count = Predication.query_predication_count(session, document_collection=document_collection)
    logging.info(f"Found {count} triples")
    prog = Progress(total=count, text="Building Graph", print_every=100)
    output_graph = rdflib.Graph()
    prog.start_time()
    for n, row in enumerate(Predication.iterate_predications(session, document_collection=document_collection)):
        output_graph.add((rdflib.URIRef(row.subject_id),
                          rdflib.URIRef(row.predicate_canonicalized),
                          rdflib.URIRef(row.object_id)))
        prog.print_progress(n+1)
    prog.done()
    logging.info(f"Writing graph to {output_file}...")
    output_graph.serialize(destination=output_file, format="turtle")
    logging.info("done!")


def export_predications_as_tsv(output_file:str, document_collection=None, export_metadata=False):
    """
    Exports the database tuples as a CSV
    :param output_file: output filename
    :param document_collection: only export statements in this document collection (optional)
    :param export_metadata: if true metadata will also be extracted
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
    parser.add_argument("-f", "--format", action='store', choices=["rdf", "tsv"],
                        help='export format (supported: rdf (turtle) | tsv)', required=True)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    if args.format.lower() == 'rdf':
        export_predications_as_rdf(args.output, document_collection=args.collection)
    else:
        export_predications_as_tsv(args.output, document_collection=args.collection, export_metadata=args.metadata)


if __name__ == "__main__":
    main()
