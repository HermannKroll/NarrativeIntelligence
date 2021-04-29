import argparse
import logging
from collections import defaultdict

from narant.backend.database import Session
from narant.backend.export import create_tag_query
from narant.backend.models import Document, Tag
from narraint.entity.enttypes import TAG_TYPE_MAPPING
from narraint.pubtator.extract import read_pubtator_documents
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS


def load_all_tags_for_doc_ids(doc_ids, collection, tag_types):
    """
    loads the database entity tags for a list of doc_ids
    :param doc_ids: sequence of doc_ids
    :param collection: document collection
    :param tag_types: the tag types toxport
    :return: a dict mapping document ids to tuples (ent_id, ent_str, ent_type)
    """
    session = Session.get()
    # get all tags for the given doc_ids
    query = create_tag_query(session, collection, doc_ids, tag_types=tag_types)

    doc2tags = defaultdict(list)
    counter = 0
    for tag in query:
        t = (tag.ent_id, tag.ent_str, tag.ent_type, tag.start, tag.end)
        doc2tags[int(tag.document_id)].append(t)
        counter += 1
    logging.info('{} tags load from db'.format(counter))
    return doc2tags


def enrich_pubtator_documents_with_database_tags(input_dir, output_file, document_collection, tag_types):
    """
    Enriches a pubtator documents with tags queried from the database
    :param input_dir: input dir or file of pubtator files
    :param output_file: the resulting output file
    :param document_collection: the document collection
    :param tag_types: the tag types which should be exported
    :return:
    """
    logging.info('Scanning for documents...')
    doc_ids = set()
    for idx, pubtator_content in enumerate(read_pubtator_documents(input_dir)):
        match = CONTENT_ID_TIT_ABS.match(pubtator_content)
        if match:
            doc_id, doc_title, doc_content = match.group(1, 2, 3)
            doc_ids.add(doc_id)
    logging.info('Loading tags for {} documents in collection: {}'.format(len(doc_ids), document_collection))
    doc2tags = load_all_tags_for_doc_ids(doc_ids, document_collection, tag_types)

    logging.info('Producing new output in {}'.format(output_file))
    with open(output_file, 'wt') as f:
        for idx, pubtator_content in enumerate(read_pubtator_documents(input_dir)):
            match = CONTENT_ID_TIT_ABS.match(pubtator_content)
            if match:
                doc_id, doc_title, doc_content = match.group(1, 2, 3)
                doc_id = int(doc_id)
                if doc_id in doc2tags:
                    content = Document.create_pubtator(doc_id, doc_title, doc_content)
                    f.write(content)
                    tags = doc2tags[doc_id]
                    for t in tags:
                        e_id, e_str, e_type, e_start, e_end = t
                        tag_line = Tag.create_pubtator(doc_id, e_start, e_end, e_str, e_type, e_id)
                        f.write(tag_line)
                    f.write('\n')
    logging.info('Finished')


def main():
    """

    Input: Directory with Pubtator files
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="single pubtator file (containing multiple documents) or directory of "
                                      "pubtator files")
    parser.add_argument("output", help="PubTator output file with tag results")
    parser.add_argument("--collection", required=True, help="The document collection")
    parser.add_argument("-t", "--tag", choices=TAG_TYPE_MAPPING.keys(), nargs="+")

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    enrich_pubtator_documents_with_database_tags(args.input, args.output, args.collection, args.tag)


if __name__ == "__main__":
    main()
