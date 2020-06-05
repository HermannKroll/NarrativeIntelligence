import argparse
import logging

from narraint.entity import enttypes
from narraint.backend.database import Session
from narraint.entity.enttypes import TAG_TYPE_MAPPING, SPECIES, GENE
from narraint.backend.models import Document, Tag
from narraint.entity.entityresolver import EntityResolver
from narraint.pubtator.translation.patent import PatentConverter

CONTENT_BUFFER_SIZE = 10000
TAG_BUFFER_SIZE = 100000


def export(out_fn, tag_types, document_ids=None, collection=None, content=True, logger=logging,
           content_buffer=CONTENT_BUFFER_SIZE, tag_buffer=TAG_BUFFER_SIZE):
    """
    Exports tagged documents in the database as a single PubTator file
    :param out_fn: path of file
    :param tag_types: set of types which should be exported
    :param document_ids: set of document ids which should be exported, None = All
    :param collection: document collection which should be exported, None = All
    :param content: if true, title and abstract are exported as well, if false only tags are exported
    :param logger: logging class
    :param content_buffer: buffer how much document contents should be retrieved from the database in one chunk
    :param tag_buffer: buffer how much tags should be retrieved from the database in one chunk
    :return:
    """
    logger.info("Beginning export...")
    if document_ids is None:
        document_ids = []
    else:
        logger.info('Using {} ids for a filter condition'.format(len(document_ids)))

    session = Session.get()

    if content:
        document_query = create_document_query(session, collection,  document_ids, content_buffer)
    if tag_types:
        tag_query = create_tag_query(session, collection, document_ids, tag_types, tag_buffer)

    if content and not tag_types:
        with open(out_fn, "w") as f:
            for document in document_query:
                f.write(Document.create_pubtator(document.id, document.title, document.abstract) + "\n")

    elif not content and tag_types:
        with open(out_fn, "w") as f:
            for tag in tag_query:
                f.write(Tag.create_pubtator(tag.document_id, tag.start, tag.end, tag.ent_str, tag.ent_type, tag.ent_id))

    elif content and tag_types:
        content_iter = iter(document_query)
        current_document = None
        first_doc = True
        with open(out_fn, "w") as f:
            for tag in tag_query:
                # skip to tagged document
                while not current_document or not (
                        tag.document_id == current_document.id
                        and tag.document_collection == current_document.collection):
                    current_document = next(content_iter)
                    if not first_doc:
                        f.write("\n")
                    first_doc = False
                    f.write(Document.create_pubtator(current_document.id, current_document.title,
                                                     current_document.abstract))
                f.write(Tag.create_pubtator(tag.document_id, tag.start, tag.end, tag.ent_str, tag.ent_type, tag.ent_id))

            # Write tailing documents with no tags
            current_document = next(content_iter, None)
            while current_document:
                if not first_doc:
                    f.write("\n")
                first_doc = False
                f.write(Document.create_pubtator(current_document.id, current_document.title,
                                                 current_document.abstract))
                current_document = next(content_iter, None)
            # end export with a new line
            f.write("\n")


def create_tag_query(session, collection=None, document_ids=None, tag_types=None, tag_buffer=TAG_BUFFER_SIZE):
    tag_query = session.query(Tag).yield_per(tag_buffer)
    if collection:
        tag_query = tag_query.filter_by(document_collection=collection)
    if tag_types and enttypes.ALL != tag_types:
        tag_query = tag_query.filter(Tag.ent_type.in_(tag_types))
    if document_ids:
        tag_query = tag_query.filter(Tag.document_id.in_(document_ids))
    tag_query = tag_query.order_by(Tag.document_collection, Tag.document_id, Tag.ent_type, Tag.start, Tag.id )
    return tag_query


def create_document_query(session, collection=None, document_ids=None, content_buffer=CONTENT_BUFFER_SIZE):
    document_query = session.query(Document).yield_per(content_buffer)
    if collection:
        document_query = document_query.filter_by(collection=collection)
    if document_ids:
        document_query = document_query.filter(Document.id.in_(document_ids))
    document_query = document_query.order_by(Document.collection, Document.id)
    return document_query


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
    logger = logging.getLogger("export")
    if args.sqllog:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    tag_types = []
    if args.tag:
        tag_types = enttypes.ALL if "A" in args.tag else [TAG_TYPE_MAPPING[x] for x in args.tag]

    if args.ids:
        document_ids = [int(x) for x in args.ids]
    elif args.idfile:
        logger.info('reading id file: {}'.format(args.idfile))
        with open(args.idfile, 'r') as f:
            document_ids = list(set([int(line.strip()) for line in f]))
        logger.info('{} ids retrieved from id file..'.format(len(document_ids)))
    else:
        document_ids = None

    if args.patents:
        parser.error('Does not support patent ids replacement in pubtator mode')

    export(args.output, tag_types, document_ids, collection=args.collection, content=args.document, logger=logger)

if __name__ == "__main__":
    main()
