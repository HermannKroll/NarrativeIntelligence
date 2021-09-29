import logging

from sqlalchemy import delete, and_

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, DocumentMetadata, DocumentMetadataService, Document


def compute_document_metadata_service_table():
    """
    Computes the DocumentMetadataService table
    Titles and Metadata will be queried from Document and DocumentMetadata
    And only document ids that have at least a single extraction (Predication) will be considered
    :return: None
    """
    session = SessionExtended.get()

    logging.info('Deleting old service metadata...')
    stmt = delete(DocumentMetadataService)
    session.execute(stmt)

    logging.info('Querying document collections the predication table...')
    q_p_ids = session.query(Predication.document_collection.distinct()) \
        .filter(Predication.relation.isnot(None))
    document_collections = set()
    for r in q_p_ids:
        document_collections.add(r[0])

    logging.info(f'Found {len(document_collections)} document collections...')
    for d_col in document_collections:
        sub_query = session.query(Predication.document_id) \
            .filter(Predication.relation.isnot(None)) \
            .filter(Predication.document_collection == d_col)

        logging.info(f'Querying titles for collection: {d_col}')
        title_query = session.query(Document.id, Document.title).filter(and_(Document.collection == d_col,
                                                                             Document.id.in_(sub_query)))
        doc2titles = {}
        for r in title_query:
            doc2titles[int(r[0])] = r[1]
        logging.info(f'{len(doc2titles)} document titles were found')

        logging.info(f'Querying metadata for collection: {d_col}')
        meta_query = session.query(DocumentMetadata).filter(and_(DocumentMetadata.document_id.in_(sub_query),
                                                                 DocumentMetadata.document_collection == d_col))

        doc2metadata = {}
        for r in meta_query:
            doc2metadata[r.document_id] = (r.authors, r.journals, r.publication_year)
        logging.info(f'{len(doc2metadata)} document metadata were found')

        logging.info('Preparing insert....')
        # prepare insert
        insert_values = []
        for d_id, title in doc2titles.items():
            if d_id in doc2metadata:
                authors, journals, publication_year = doc2metadata[d_id]
            else:
                # skip documents that does not have this information avialbe
                continue
            if publication_year == 'None' or not publication_year:
                continue
            insert_values.append(dict(document_id=d_id, document_collection=d_col, title=title,
                                      authors=authors, journals=journals, publication_year=publication_year))
        logging.info(f'Inserting {len(insert_values)} into database table DocumentMetadataService...')
        DocumentMetadataService.bulk_insert_values_into_table(session, insert_values)
        logging.info('Finished')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    compute_document_metadata_service_table()


if __name__ == "__main__":
    main()
