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
    parser.add_argument("--log", action="store_true")
    args = parser.parse_args()

    if not (args.tag or args.document):
        parser.error('No action requested, add -d or -t')

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

    results = query.all()
    print("Number of results: ", len(results))
    if args.document and args.tag:
        with open(args.output, "w") as f:
            doc = None
            for document, tag in results:
                if doc != document:
                    if doc is not None:
                        f.write("\n")
                    f.write(document.to_pubtator())
                    doc = document
                f.write(tag.to_pubtator())
    elif args.document:
        with open(args.output, "w") as f:
            for document in results:
                f.write(document.to_pubtator() + "\n")
    else:
        with open(args.output, "w") as f:
            for tag in results:
                f.write(tag.to_pubtator())
    print("Results written to {}".format(args.output))


if __name__ == "__main__":
    main()
