import argparse
import logging

from narraint.entity import enttypes
from narraint.backend.database import Session
from narraint.entity.enttypes import TAG_TYPE_MAPPING
from narraint.backend.models import Document, Tag
from narraint.entity.entityresolver import EntityResolver
from narraint.pubtator.convert import PatentConverter


def export(out_fn, tag_types, document_ids=None, collection=None, content=True, logger=logging):
    logger.info("Beginning export...")
    if document_ids is None:
        document_ids = []
    else:
        logger.info('Using {} ids for a filter condition'.format(len(document_ids)))

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
    if logger:
        logger.info("Results written to {}".format(out_fn))


def export_xml(out_fn, tag_types, document_ids=None, collection=None, logger=None, patent_ids=False):
    logging.info("Beginning XML export...")
    if document_ids is None:
        document_ids = []
    else:
        logging.info('Using {} ids for a filter condition'.format(len(document_ids)))

    session = Session.get()
    query = session.query(Tag.document_id, Tag.ent_id, Tag.ent_type)
    if collection:
        query = query.filter_by(document_collection=collection)
    if document_ids:
        query = query.filter(Tag.document_id.in_(document_ids))
    query = query.order_by(Tag.document_collection, Tag.document_id, Tag.id)

    if tag_types and enttypes.ALL != tag_types:
        query = query.filter(Tag.ent_type.in_(tag_types))

    results = session.execute(query)
    entity_resolver = EntityResolver()
    tags_for_doc = set()
    last_doc_id = -1
    doc_count = 0
    translation_errors = 0
    missing_ent_ids = set()
    with open(out_fn, 'wt', encoding="utf-8") as f:
        f.write("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n")
        f.write("<documents>\n")
        for row in results:
            doc_id, ent_id, ent_type = row
            # collect tags for document (as long as tags are for the same document)
            if last_doc_id == -1:
                last_doc_id = doc_id
            if doc_id == last_doc_id:
                tags_for_doc.add((ent_id, ent_type))
                continue
            else:
                doc_count += 1
                doc_xml_content = []
                if tags_for_doc:
                    # create element with all tags for this document
                    doc_xml_content.append("\t<document>\n")
                    if patent_ids:
                        doc_id = str(PatentConverter.decode_patent_country_code(doc_id))
                    else:
                        doc_id = str(doc_id)
                    doc_xml_content.append("\t\t<id>{}</id>\n".format(doc_id))
                    count_translated = 0
                    for e_id, e_type in tags_for_doc:
                        try:
                            doc_xml_content.append("\t\t<tag>{}</tag>\n"
                                                   .format(entity_resolver.get_name_for_var_ent_id(e_id, e_type)))
                            count_translated += 1
                        except KeyError:
                            missing_ent_ids.add((e_id, e_type))
                            translation_errors += 1
                            continue
                            # logger.warning('Does not know how to translate: {}'.format(e_id))
                    doc_xml_content.append("\t</document>\n")
                    doc_xml_temp = "".join(doc_xml_content)
                    if count_translated:
                        f.write(doc_xml_temp)
                last_doc_id = doc_id
                tags_for_doc = set()
        f.write("</documents>")
    if logger:
        logger.warning('the following entity ids are missing: {}'.format(missing_ent_ids))
        logger.warning('{} entity tags skips due to missing translations'.format(translation_errors))
        logger.info("{} documents with their tags written to {}".format(doc_count, out_fn))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--ids", nargs="*", metavar="DOC_ID")
    parser.add_argument("--idfile", help='file containing document ids (one id per line)')
    parser.add_argument("-c", "--collection", help="Collection(s)", default=None)
    parser.add_argument("-p", "--patents", action="store_true", help="Will replace the patent prefix ids by country codes")
    parser.add_argument("-d", "--document", action="store_true", help="Export content of document")
    parser.add_argument("-t", "--tag", choices=TAG_TYPE_MAPPING.keys(), nargs="+")
    parser.add_argument("--sqllog", action="store_true", help='logs sql commands')
    parser.add_argument("-f", "--format", help="Export format (Pubtator / XML)", default="Pubtator")
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

    if args.format == 'Pubtator':
        if args.patents:
            parser.error('Does not support patent ids replacement in pubtator mode')

        export(args.output, tag_types, document_ids, collection=args.collection, content=args.document, logger=logger)
    elif args.format == 'XML':
        if args.document:
            parser.error('Does not support document content in XML mode')
        if args.patents:
            export_xml(args.output, tag_types, document_ids, collection=args.collection, logger=logger,
                       patent_ids=True)
        else:
            export_xml(args.output, tag_types, document_ids, collection=args.collection, logger=logger,
                       patent_ids=False)


    else:
        parser.error('Does not support unknown format: {}'.format(args.format))


if __name__ == "__main__":
    main()
