import argparse
import logging
import os

from narraint.backend import enttypes
from narraint.backend.database import Session
from narraint.backend.enttypes import TAG_TYPE_MAPPING
from narraint.backend.models import Document, Tag


def export(out_fn, tag_types, document_ids=None, collection=None, content=True):
    logging.info("beginning export...")
    if document_ids is None:
        document_ids = []
    else:
        logging.info('using {} ids for a filter condition'.format(len(document_ids)))

    session = Session.get()
    if content and tag_types:
        query = session.query(Document, Tag)
        if collection:
            query = query.filter_by(collection=collection)
        if document_ids:
            query = query.filter(Document.id.in_(document_ids))
        query = query.join(Tag)
        query = query.order_by(Document.collection, Document.id, Tag.id)
    elif content:
        query = session.query(Document)
        if collection:
            query = query.filter_by(collection=collection)
        if document_ids:
            query = query.filter(Document.id.in_(document_ids))
        query = query.order_by(Document.collection, Document.id)
    else:
        query = session.query(Tag)
        if collection:
            query = query.filter_by(document_collection=collection)
        if document_ids:
            query = query.filter(Tag.document_id.in_(document_ids))
        query = query.order_by(Tag.document_collection, Tag.document_id, Tag.id)

    if tag_types and enttypes.ALL != tag_types:
        query = query.filter(Tag.ent_type.in_(tag_types))

    results = session.execute(query)
    if content and tag_types:
        with open(out_fn, "w") as f:
            doc_id = None
            for row in results:
                if doc_id != row[1]:  # row[1] is document ID
                    if doc_id:
                        f.write("\n")
                    f.write(Document.create_pubtator(row[1], row[2], row[3]))
                    doc_id = row[1]
                f.write(Tag.create_pubtator(row[1], row[8], row[9], row[11], row[7], row[10]))
    elif content:
        with open(out_fn, "w") as f:
            for row in results:
                f.write(Document.create_pubtator(row[1], row[2], row[3]) + "\n")
    else:
        with open(out_fn, "w") as f:
            for row in results:
                f.write(Tag.create_pubtator(row[6], row[2], row[3], row[5], row[1], row[4]))
    logging.info("Results written to {}".format(out_fn))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--ids", nargs="*", metavar="DOC_ID")
    parser.add_argument("--idfile", help='file containing document ids (one id per line)')
    parser.add_argument("-c", "--collection", help="Collection(s)", default=None)
    parser.add_argument("-d", "--document", action="store_true", help="Export content of document")
    parser.add_argument("-t", "--tag", choices=TAG_TYPE_MAPPING.keys(), nargs="+")
    parser.add_argument("--sqllog", action="store_true", help='logs sql commands')
    args = parser.parse_args()

    if not (args.tag or args.document):
        parser.error('No action requested, add -d or -t')

    if args.ids and args.idfile:
        parser.error('Does not support a list of ids and an ids file')

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    if args.sqllog:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    tag_types = []
    if args.tag:
        tag_types = enttypes.ALL if "A" in args.tag else [TAG_TYPE_MAPPING[x] for x in args.tag]

    if args.ids:
        document_ids = [int(x) for x in args.ids]
    elif args.idfile:
        logging.info('reading id file: {}'.format(args.idfile))
        with open(args.idfile, 'r') as f:
            document_ids = list(set([int(line.strip()) for line in f]))
        logging.info('{} ids retrieved from id file..'.format(len(document_ids)))
    else:
        document_ids = None

    export(args.output, tag_types, document_ids, collection=args.collection, content=args.document)


if __name__ == "__main__":
    main()
