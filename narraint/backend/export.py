import argparse
import logging
import re

from narraint.backend.database import Session
from narraint.backend.models import Document, Tag

PUBTATOR_REGEX = re.compile(r"(\d+)\|t\|(.*?)\n\d+\|a\|(.*?)\n")
TAG_REGEX = re.compile(r"(\d+)\t(\d+)\t(\d+)\t(.*?)\t(.*?)\t(.*?)\n")
PUBTATOR_CONTENT_REGEX = re.compile(r"\d+.*?\n\n", re.DOTALL)

TAG_TYPE_MAPPING = dict(
    DF="DosageForm",
    C="Chemical",
    M="Mutation",
    G="Gene",
    S="Species",
    D="Disease",
    A="ALL",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("-c", "--collection", help="Collection(s)")
    parser.add_argument("-d", "--document", action="store_true", help="Export content of document")
    parser.add_argument("-t", "--tag", choices=TAG_TYPE_MAPPING.keys(), nargs="+")
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--log", action="store_true")
    args = parser.parse_args()

    if args.log:
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    session = Session.get()
    if args.document and args.tag:
        query = session.query(Document, Tag)
        if args.collection:
            query = query.filter_by(collection=args.collection)
        query = query.join(Tag)
        if "A" not in args.tag:
            query = query.filter(Tag.type.in_([TAG_TYPE_MAPPING[x] for x in args.tag]))
        query = query.order_by(Document.collection, Document.id, Tag.id)
    elif args.document:
        query = session.query(Document)
        if args.collection:
            query = query.filter_by(collection=args.collection)
        query = query.order_by(Document.collection, Document.id)
    else:
        query = session.query(Tag)
        if args.collection:
            query = query.filter_by(document_collection=args.collection)
        query = query.order_by(Tag.document_collection, Tag.document_id, Tag.id)

    if args.tag and "A" not in args.tag:
        query = query.filter(Tag.type.in_([TAG_TYPE_MAPPING[x] for x in args.tag]))

    print("Query: ", query)
    results = query.all()
    print("Number of results: ", len(results))
    # TODO: Write to disk (with merge feature)
    if args.document and args.tag:
        pass
    elif args.document:
        pass
    else:
        pass


if __name__ == "__main__":
    main()
