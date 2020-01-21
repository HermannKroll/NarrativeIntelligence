import argparse
import logging

from narraint.backend import enttypes
from narraint.backend.database import Session
from narraint.backend.models import Document, Tag
from narraint.backend.enttypes import TAG_TYPE_MAPPING


# TODO: Make memory-sensitive
def export(out_fn, tag_types, document_ids=None, collection=None, content=True):
    if document_ids is None:
        document_ids = []
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

    results = query.all()
    if content and tag_types:
        with open(out_fn, "w") as f:
            doc = None
            for document, tag in results:
                if doc != document:
                    if doc is not None:
                        f.write("\n")
                    f.write(document.to_pubtator())
                    doc = document
                f.write(tag.to_pubtator())
    elif content:
        with open(out_fn, "w") as f:
            for document in results:
                f.write(document.to_pubtator() + "\n")
    else:
        with open(out_fn, "w") as f:
            for tag in results:
                f.write(tag.to_pubtator())
    print("Results written to {}".format(out_fn))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("ids", nargs="*", metavar="DOC_ID")
    parser.add_argument("-c", "--collection", help="Collection(s)", default=None)
    parser.add_argument("-d", "--document", action="store_true", help="Export content of document")
    parser.add_argument("-t", "--tag", choices=TAG_TYPE_MAPPING.keys(), nargs="+")
    parser.add_argument("--log", action="store_true")
    args = parser.parse_args()

    if not (args.tag or args.document):
        parser.error('No action requested, add -d or -t')

    if args.log:
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    tag_types = []
    if args.tag:
        tag_types = enttypes.ALL if "A" in args.tag else [TAG_TYPE_MAPPING[x] for x in args.tag]

    document_ids = [int(x) for x in args.ids]

    export(args.output, tag_types, document_ids, collection=args.collection, content=args.document)


if __name__ == "__main__":
    main()
