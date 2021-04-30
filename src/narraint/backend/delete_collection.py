import argparse
import logging

from narraint.backend.database import Session
from narraint.backend.models import Tag, Document, DocTaggedBy, DocProcessedByIE, Predication


def delete_document_collection_from_database(document_collection: str):
    logging.info('Beginning deletion of document collection: {}'.format(document_collection))
    session = Session.get()

    logging.info('Deleting doc_processed_by_ie entries...')
    session.query(DocProcessedByIE).filter(DocProcessedByIE.document_collection == document_collection).delete()

    logging.info('Deleting predication entries...')
    session.query(Predication).filter(Predication.document_collection == document_collection).delete()

    logging.info('Deleting doc_tagged_by entries...')
    session.query(DocTaggedBy).filter(DocTaggedBy.document_collection == document_collection).delete()

    logging.info('Deleting tag entries...')
    session.query(Tag).filter(Tag.document_collection == document_collection).delete()

    logging.info('Deleting document entries...')
    session.query(Document).filter(Document.collection == document_collection).delete()

    logging.info('Begin commit...')
    session.commit()
    logging.info('Commit complete - document collection deleted')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("collection")
    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    collection = args.collection
    logging.info('Counting documents for collection: {}'.format(collection))
    session = Session.get()
    doc_count = session.query(Document.id.distinct()).filter(Document.collection == collection).count()
    logging.info('{} documents found'.format(doc_count))
    print('{} documents are found'.format(doc_count))
    print('Are you really want to delete all documents? This will also delete all corresponding tags (Tag), '
          'tagging information (doc_taggedb_by), facts (Predication) and extraction information (doc_processed_by_ie)')
    answer = input('Enter y(yes) to proceed the deletion...')
    if answer.lower() == 'y' or answer.lower() == 'yes':
        delete_document_collection_from_database(collection)
        logging.info('Finished')
    else:
        print('Canceled')


if __name__ == "__main__":
    main()