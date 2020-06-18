import argparse
import logging
from collections import defaultdict

from narraint.backend.database import Session
from narraint.backend.models import Document, Tag
from narraint.pubtator.extract import read_pubtator_documents
from narraint.pubtator.regex import CONTENT_ID_TIT_ABS


def load_tags_for_doc_ids_complete(doc_ids, collection):
    """
    loads the database entity tags for a list of doc_ids
    :param doc_ids: sequence of doc_ids
    :param collection: document collection
    :return: a dict mapping document ids to tuples (ent_id, ent_str, ent_type)
    """
    session = Session.get()
    # get all tags for the given doc_ids
    query = session.query(Tag.document_id, Tag.ent_id, Tag.ent_str, Tag.ent_type, Tag.start, Tag.end)
    query = query.filter(Tag.document_collection == collection)
    query = query.filter(Tag.document_id.in_(doc_ids))

    doc2tags = defaultdict(list)
    results = session.execute(query)
    counter = 0
    for row in results:
        ent_str = ' {} '.format(row[2]).lower()
        t = (row[1], ent_str, row[3], row[4], row[5])
        doc2tags[int(row[0])].append(t)
        counter += 1
    logging.info('{} tags load from db'.format(counter))
    return doc2tags


def main():
    """

    Input: Directory with Pubtator files
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="single pubtator file (containing multiple documents) or directory of "
                                      "pubtator files")
    parser.add_argument("output", help="File with OpenIE results")
    parser.add_argument("--collection",  required=True, help="File with OpenIE results")
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logging.info('Scanning for documents...')
    doc_ids = set()
    for idx, pubtator_content in enumerate(read_pubtator_documents(args.input)):
        match = CONTENT_ID_TIT_ABS.match(pubtator_content)
        if match:
            doc_id, doc_title, doc_content = match.group(1, 2, 3)
            doc_ids.add(doc_id)
    logging.info('Loading tags for {} documents in collection: {}'.format(len(doc_ids), args.collection))
    doc2tags = load_tags_for_doc_ids_complete(doc_ids, args.collection)

    logging.info('Producing new output in {}'.format(args.output))
    with open(args.output, 'wt') as f:
        for idx, pubtator_content in enumerate(read_pubtator_documents(args.input)):
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

if __name__ == "__main__":
    main()
