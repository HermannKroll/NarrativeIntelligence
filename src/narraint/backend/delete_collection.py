import argparse
import logging

from sqlalchemy import delete

from kgextractiontoolbox.backend.delete_collection import delete_document_collection_from_database
from kgextractiontoolbox.backend.models import Document
from narraint.backend.database import SessionExtended
from narraint.backend.models import DocumentMetadata, TagInvertedIndex, DocumentMetadataService, TermInvertedIndex


def delete_document_collection_from_database_enhanced(document_collection: str):
    logging.info('Beginning deletion of document collection: {}'.format(document_collection))
    session = SessionExtended.get()

    logging.info('Deleting document_metadata_service entries...')
    session.execute(
        delete(DocumentMetadataService).where(DocumentMetadataService.document_collection == document_collection))

    logging.info('Deleting document_metadata entries...')
    session.execute(delete(DocumentMetadata).where(DocumentMetadata.document_collection == document_collection))

    logging.info('Deleting tag_inverted_index entries...')
    session.execute(delete(TagInvertedIndex).where(TagInvertedIndex.document_collection == document_collection))

    logging.info('Deleting term_inverted_index entries...')
    session.execute(delete(TermInvertedIndex).where(TermInvertedIndex.document_collection == document_collection))

    logging.info('Begin commit...')
    session.commit()
    logging.info('Commit complete - document collection deleted')

    delete_document_collection_from_database(document_collection)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("collection")
    parser.add_argument("-f", "--force", help="skip user confirmation for deletion", action="store_true")

    args = parser.parse_args()
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    collection = args.collection
    logging.info('Counting documents for collection: {}'.format(collection))
    session = SessionExtended.get()
    doc_count = session.query(Document.id.distinct()).filter(Document.collection == collection).count()
    logging.info('{} documents found'.format(doc_count))
    answer = None
    if not args.force:
        print('{} documents are found'.format(doc_count))
        print('Are you really want to delete all documents? This will also delete all corresponding tags (Tag), '
              'tagging information (doc_taggedb_by), facts (Predication) and extraction information (doc_processed_by_ie)')
        answer = input('Enter y(yes) to proceed the deletion...')
    if args.force or (answer and (answer.lower() == 'y' or answer.lower() == 'yes')):
        delete_document_collection_from_database_enhanced(collection)
        logging.info('Finished')
    else:
        print('Canceled')


if __name__ == "__main__":
    main()
