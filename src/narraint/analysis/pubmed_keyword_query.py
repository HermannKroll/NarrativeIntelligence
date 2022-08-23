import logging

from narraint.backend.database import SessionExtended
from narraint.backend.models import DocProcessedByOpenIE
from narraint.pubmedutils import pubmed_crawl_pmids

document_collections = ["PubMed"]
keyword_queries = ["Simvastatin Cholesterol"]


# document_collections = ["PubMed", "PMC"]
# keyword_queries = ["Simvastatin Rhabdomyolysis", "Simvastatin Cholesterol", "Metformin Diabetes Mellitus",
#                   "Metformin MTOR"]


def retrieve_ids_in_openie_database(document_collection):
    session = SessionExtended.get()
    logging.info('Querying for document ids processed by OpenIE in collection: {}'.format(document_collection))
    q = session.query(DocProcessedByOpenIE.document_id).filter_by(document_collection=document_collection)
    document_ids = set()
    for row in session.execute(q):
        document_ids.add(int(row[0]))
    logging.info('{} ids retrieved'.format(len(document_ids)))
    return document_ids


def apply_keyword_query(query, document_collection):
    pubmed_ids = pubmed_crawl_pmids(query, "kroll@ifis.cs.tu-bs.de", "kroll-experiment-2020", document_collection)
    return set([int(doc_id) for doc_id in pubmed_ids])


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    for collection in document_collections:
        logging.info('Processing document collection: {}'.format(collection))
        doc_ids_in_db = retrieve_ids_in_openie_database(collection)
        for q in keyword_queries:
            logging.info('Processing query: {}'.format(q))
            pubmed_doc_ids = apply_keyword_query(q, collection)
            logging.info('{} document ids retrieved from PubMed'.format(len(pubmed_doc_ids)))
            pubmed_doc_ids_in_db = pubmed_doc_ids.intersection(doc_ids_in_db)

            with open("ids.txt", "wt") as f:
                for doc_id in pubmed_doc_ids_in_db:
                    f.write(str(doc_id) + '\n')
            # logging.info('{} documents have been processed by OpenIE and are in database'.format(len(pubmed_doc_ids_in_db)))
            # pubmed_doc_ids_in_db_sample = random.sample(pubmed_doc_ids_in_db, 25)
            # logging.info('The following ids were sampled: {}'.format(pubmed_doc_ids_in_db_sample))


if __name__ == "__main__":
    main()
