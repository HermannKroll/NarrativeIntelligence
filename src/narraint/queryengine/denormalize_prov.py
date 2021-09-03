import json
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import and_

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, DocumentMetadataService
from narraint.backend.models import PredicationDenorm
from narraint.config import BULK_INSERT_AFTER_K, QUERY_YIELD_PER_K
from narrant.progress import print_progress_with_eta


def denormalize_predication_table():
    session = SessionExtended.get()
    logging.info('Counting the number of predications...')
    pred_count = session.query(Predication).filter(Predication.relation != None).count()

    start_time = datetime.now()
    # "is not None" instead of "!=" None" DOES NOT WORK!
    prov_query = session.query(Predication).filter(Predication.relation != None)\
        .join(DocumentMetadataService, and_(Predication.document_id == DocumentMetadataService.document_id,
                                            Predication.document_collection == DocumentMetadataService.document_collection)) \
        .yield_per(QUERY_YIELD_PER_K)

    insert_list = []
    logging.info("Starting...")
    fact_to_doc_ids = defaultdict(lambda: defaultdict(list))
    fact_to_prov_ids = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for idx, prov in enumerate(prov_query):
        print_progress_with_eta("denormalizing", idx, pred_count, start_time)
        s_id = prov.subject_id
        s_t = prov.subject_type
        p = prov.relation
        o_id = prov.object_id
        o_t = prov.object_type
        seen_key = (s_id, s_t, p, o_id, o_t)
        fact_to_doc_ids[seen_key][prov.document_collection].append(prov.document_id)
        fact_to_prov_ids[seen_key][prov.document_collection][prov.document_id].append(prov.id)

    # Restructure dictionaries
    for k in fact_to_doc_ids:
        for v in fact_to_doc_ids[k]:
            fact_to_doc_ids[k][v] = sorted(set(fact_to_doc_ids[k][v]))

    for k in fact_to_prov_ids:
        for v in fact_to_prov_ids[k]:
            for w in fact_to_prov_ids[k][v]:
                fact_to_prov_ids[k][v][w] = sorted(set(fact_to_prov_ids[k][v][w]))

    logging.info("Beginning insert...")
    insert_time = datetime.now()

    key_count = len(fact_to_doc_ids)
    for idx, k in enumerate(fact_to_doc_ids):
        print_progress_with_eta("inserting values", idx, key_count, insert_time, print_every_k=100)
        if idx % BULK_INSERT_AFTER_K == 0:
            PredicationDenorm.bulk_insert_values_into_table(session, insert_list)
            insert_list.clear()
        insert_list.append(dict(
            subject_id=k[0],
            subject_type=k[1],
            relation=k[2],
            object_id=k[3],
            object_type=k[4],
            #     document_ids=json.dumps(fact_to_doc_ids[k]),
            provenance_mapping=json.dumps(fact_to_prov_ids[k])
        ))

    PredicationDenorm.bulk_insert_values_into_table(session, insert_list)
    insert_list.clear()

    end_time = datetime.now()
    logging.info(f"Query table created. Took me {end_time - start_time} minutes.")


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    denormalize_predication_table()


if __name__ == "__main__":
    main()
