import argparse
import logging

from sqlalchemy import delete

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, DocumentMetadata, DocumentMetadataService, Document, \
    DocumentClassification

BULK_QUERY_CURSOR_COUNT = 500000


def compute_document_metadata_service_table(rebuild=False):
    """
    Computes the DocumentMetadataService table
    Titles and Metadata will be queried from Document and DocumentMetadata
    And only document ids that have at least a single extraction (Predication) will be considered
    :return: None
    """
    session = SessionExtended.get()

    if rebuild:
        logging.info('Deleting old service metadata...')
        stmt = delete(DocumentMetadataService)
        session.execute(stmt)
        session.commit()

    logging.info('Querying document collections the predication table...')
    q_p_ids = session.query(Predication.document_collection.distinct()) \
        .filter(Predication.relation.isnot(None))
    document_collections = set()
    for r in q_p_ids:
        document_collections.add(r[0])

    logging.info(f'Found {len(document_collections)} document collections...')
    for d_col in document_collections:
        logging.info(f'Querying relevant document ids from Predication table for collection: {d_col}')
        pred_query = session.query(Predication.document_id) \
            .filter(Predication.relation.isnot(None)) \
            .filter(Predication.document_collection == d_col).distinct()
        relevant_doc_ids = set()
        for row in pred_query:
            relevant_doc_ids.add(row[0])
        logging.info(f'Found {len(relevant_doc_ids)} relevant document ids in predication table...')

        logging.info('Querying document ids that have metadata in DocumentMetadataService table...')
        aq = session.query(DocumentMetadataService.document_id)
        aq = aq.filter(DocumentMetadataService.document_collection == d_col)
        document_ids_with_metadata = set()
        for row in aq:
            document_ids_with_metadata.add(int(row[0]))
        logging.info(f'{len(document_ids_with_metadata)} have already metadata in DocumentMetadataService table')
        relevant_doc_ids = relevant_doc_ids - document_ids_with_metadata
        logging.info(f'{len(relevant_doc_ids)} relevant document ids remaining to insert...')

        logging.info(f'Querying titles for collection: {d_col}')
        title_query = session.query(Document.id, Document.title).filter(Document.collection == d_col).yield_per(
            BULK_QUERY_CURSOR_COUNT)
        doc2titles = {}
        for r in title_query:
            doc_id = int(r[0])
            if doc_id in relevant_doc_ids:
                doc2titles[doc_id] = r[1]
        logging.info(f'{len(doc2titles)} document titles were found')

        logging.info(f'Querying metadata for collection: {d_col}')
        meta_query = session.query(DocumentMetadata).filter(DocumentMetadata.document_collection == d_col).yield_per(
            BULK_QUERY_CURSOR_COUNT)

        doc2metadata = {}
        for r in meta_query:
            if r.document_id in relevant_doc_ids:
                doc2metadata[r.document_id] = (r.authors, r.journals, r.publication_year, r.publication_month,
                                               r.document_id_original, r.publication_doi)
        logging.info(f'{len(doc2metadata)} document metadata were found')

        logging.info(f'Querying classifications for collection: {d_col}')
        class_query = session.query(DocumentClassification).filter(
            DocumentClassification.document_collection == d_col).yield_per(
            BULK_QUERY_CURSOR_COUNT)
        doc2classes = {}
        for r in class_query:
            if r.document_id in relevant_doc_ids:
                if r.document_id not in doc2classes:
                    doc2classes[r.document_id] = []
                doc2classes[r.document_id].append(r.classification)
        logging.info(f'{len(doc2classes)} document classes were found')

        logging.info('Preparing insert....')
        # prepare insert
        insert_values = []
        for d_id in relevant_doc_ids:
            title = doc2titles[d_id]
            if d_id in doc2metadata:
                authors, journals, publication_year, publication_month, document_id_original, doi = doc2metadata[d_id]
                # test how many authors are there
                authors_comps = authors.split(' | ')
                if len(authors_comps) > 5:
                    authors = ' | '.join(authors_comps[:5]) + f' | {len(authors_comps) - 5}+'

            else:
                # skip documents that does not have this information available
                continue
            if publication_year == 0 or not publication_year:
                continue

            document_classes = None
            if d_id in doc2classes:
                document_classes = str(doc2classes[d_id])
            insert_values.append(dict(document_id=d_id, document_collection=d_col, title=title,
                                      authors=authors, journals=journals, publication_year=publication_year,
                                      publication_month=publication_month, document_id_original=document_id_original,
                                      publication_doi=doi, document_classifications=document_classes))
            
        logging.info(f'Inserting {len(insert_values)} into database table DocumentMetadataService...')
        DocumentMetadataService.bulk_insert_values_into_table(session, insert_values, check_constraints=True)
        logging.info('Finished')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", default=False)
    args = parser.parse_args()

    compute_document_metadata_service_table(rebuild=args.rebuild)


if __name__ == "__main__":
    main()
