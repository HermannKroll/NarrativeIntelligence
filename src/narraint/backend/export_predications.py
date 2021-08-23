import os
import typing as tp
import pathlib as pl

import logging

import argparse


import narraint.backend.database as db
import narraint.backend.models as models
from narrant.progress import Progress

import rdflib


def export(out_file:tp.Union[pl.Path,str]=None, ids=None, collection=None):
    session = db.SessionExtended.get()
    query = session.query(models.Predication)
    if collection:
        query = query.filter_by(document_collection=collection)
    if ids:
        query = query.filter(models.Predication.document_id.in_(ids))
    count = query.count()
    logging.info(f"Found {count} triples")
    prog = Progress(total=count, text="Building Graph", print_every=100)
    result = query
    output_graph = rdflib.Graph()
    prog.start_time()
    for n, row in enumerate(result):
        output_graph.add((rdflib.Literal(row.subject_id), rdflib.Literal(row.predicate), rdflib.Literal(row.object_id)))
        prog.print_progress(n+1)
    prog.done()
    logging.info(f"Writing graph to {out_file}...")
    output_graph.serialize(destination=out_file)
    logging.info("done!")


def main(args=None):
    parser = argparse.ArgumentParser("Export predications to file")
    parser.add_argument("output", help="The output file path")
    parser.add_argument("-c","--collection", help="Filter by collection")
    parser.add_argument("-i", "--ids", help="Filter by ids", nargs='*')
    parser.add_argument("-f", "--id-file", help="File containing one document id per line. Filter by these ids.")

    args = parser.parse_args(args)
    ids=[]
    if args.ids:
        ids = args.ids
    if args.id_file:
        if not os.path.isfile(args.id_file):
            logging.error(f"id file {args.id_file} doesn't exist!")
            exit(1)
        try:
            with open(args.id_file, "r") as f:
                ids += f.read().splitlines()
        except IOError:
            logging.error(f"Encountered Error while reading {args.id_file}")
            exit(1)
    export(out_file=args.output, ids=ids, collection=args.collection)



if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()