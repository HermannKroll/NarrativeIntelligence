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


def get_entity_source(entity_id, entity_type):
    entity_id_str = str(entity_id).lower()
    if entity_id_str.startswith('mesh'):
        return "MeSH"
    if entity_id_str.startswith('fid'):
        return "FID"
    if entity_type == GENE:
        return "NCBI Gene"
    if entity_type == SPECIES:
        return "NCBI Taxonomy"
    return ValueError('Don not know the source for entity: {} {}'.format(entity_id, entity_type))


def export(out_fn, tag_types, document_ids=None, collection=None, content=True, logger=logging,
           content_buffer=CONTENT_BUFFER_SIZE, tag_buffer=TAG_BUFFER_SIZE):
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
                print(document)
                f.write(Document.create_pubtator(document.id, document.title, document.abstract) + "\n")

    elif not content and tag_types:
        with open(out_fn, "w") as f:
            for tag in tag_query:
                f.write(Tag.create_pubtator(tag.document_id, tag.start, tag.end, tag.ent_str, tag.ent_type, tag.ent_id))

    elif content and tag_types:
        content_iter = iter(document_query)
        current_document = None
        with open(out_fn, "w") as f:
            for tag in tag_query:
                # skip to tagged document
                while not current_document or not (
                        tag.document_id == current_document.id
                        and tag.document_collection == current_document.collection):
                    current_document = next(content_iter)
                    f.write("\n")
                    f.write(Document.create_pubtator(current_document.id, current_document.title,
                                                     current_document.abstract))
                f.write(Tag.create_pubtator(tag.document_id, tag.start, tag.end, tag.ent_str, tag.ent_type, tag.ent_id))

            # Write tailing documents with no tags
            current_document = next(content_iter, None)
            while current_document:
                f.write("\n")
                f.write(Document.create_pubtator(current_document.id, current_document.title,
                                                 current_document.abstract))
                current_document = next(content_iter, None)


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


def export_xml(out_fn, tag_types, document_ids=None, collection=None, logger=None, patent_ids=False):
    logging.info("Beginning XML export...")
    if document_ids is None:
        document_ids = []
    else:
        logging.info('Using {} ids for a filter condition'.format(len(document_ids)))

    session = Session.get()
    query = session.query(Tag.document_id, Tag.ent_id, Tag.ent_type).yield_per(TAG_BUFFER_SIZE)
    if collection:
        query = query.filter_by(document_collection=collection)
    if document_ids:
        query = query.filter(Tag.document_id.in_(document_ids))
    query = query.order_by(Tag.document_collection, Tag.document_id, Tag.id)

    if tag_types and enttypes.ALL != tag_types:
        query = query.filter(Tag.ent_type.in_(tag_types))

    #results = session.execute(query)
    entity_resolver = EntityResolver()
    tags_for_doc = set()
    last_doc_id = -1
    doc_count = 0
    translation_errors = 0
    missing_ent_ids = set()
    with open(out_fn, 'wt', encoding="utf-8") as f:
        f.write("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n")
        f.write("<documents>\n")
        for tag in query:
            doc_id, ent_id, ent_type = (tag.document_id, tag.ent_id, tag.ent_type)
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
                            entity_name = entity_resolver.get_name_for_var_ent_id(e_id, e_type)
                            entity_source = get_entity_source(e_id, e_type)
                            if entity_source:
                                if '//' in entity_name:
                                    for e_n in entity_name.split('//'):
                                        doc_xml_content.append('\t\t<tag source="{}">{}</tag>\n'
                                                               .format(entity_source, e_n))
                                else:
                                    doc_xml_content.append('\t\t<tag source="{}">{}</tag>\n'
                                                           .format(entity_source, entity_name))
                            else:
                                doc_xml_content.append("\t\t<tag>{}</tag>\n"
                                                       .format(entity_name))
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
        logger.info("tags of {} documents written to {}".format(doc_count, out_fn))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--ids", nargs="*", metavar="DOC_ID")
    parser.add_argument("--idfile", help='file containing document ids (one id per line)')
    parser.add_argument("-c", "--collection", help="Collection(s)", default=None)
    parser.add_argument("-p", "--patents", action="store_true",
                        help="Will replace the patent prefix ids by country codes")
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
