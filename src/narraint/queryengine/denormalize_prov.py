import logging
from collections import defaultdict
from datetime import datetime
from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication
from narraint.backend.models import PredicationDenorm
from narrant.progress import print_progress_with_eta
import json




def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    session = SessionExtended.get()

    logging.info('Counting the number of predications...')
    pred_count = session.query(Predication).count()

    start_time = datetime.now()

    # prov_query = session.query(Predication.subject_id, Predication.subject_type, Predication.predicate_canonicalized,
    #                           Predication.object_id, Predication.object_type) \
    #    .filter(Predication.predicate_canonicalized != None).distinct()

    # "is not None" instead of "!=" None" DOES NOT WORK!
    prov_query = session.query(Predication).filter(Predication.predicate_canonicalized != None).yield_per(500000)

    insert_list = []

    logging.info("Starting...")

    fact_to_doc_ids = defaultdict(lambda: defaultdict(list))
    fact_to_prov_ids = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for idx, prov in enumerate(prov_query):
        print_progress_with_eta("denormalizing", idx, pred_count, start_time)
        # //id, d_id, d_col, s_id, s_str, s_t, p, p_can, o_id, o_str, o_t, conf, sen_id, extr
        s_id = prov.subject_id
        s_t = prov.subject_type
        p = prov.predicate_canonicalized
        o_id = prov.object_id
        o_t = prov.object_type
        seen_key = (s_id, s_t, p, o_id, o_t)
        fact_to_doc_ids[seen_key][prov.document_collection].append(prov.document_id)
        fact_to_prov_ids[seen_key][prov.document_collection][prov.document_id].append(prov.id)

    # nötig?
    # for k, v in fact_to_doc_ids:
    #    fact_to_doc_ids[k][v] = sorted(set(fact_to_doc_ids[k][v])) ...

    #fact_to_doc_ids = dict(fact_to_doc_ids)
    for k in fact_to_doc_ids:
        #fact_to_doc_ids[k] = dict(fact_to_doc_ids[k])
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
        print_progress_with_eta("denormalizing", idx, key_count, insert_time)
        if idx % 100000 == 0:
            session.bulk_insert_mappings(PredicationDenorm, insert_list)
            session.commit()
            insert_list.clear()
        insert_list.append(dict(
            subject_id=k[0],
            subject_type=k[1],
            predicate_canonicalized=k[2],
            object_id=k[3],
            object_type=k[4],
            document_ids=json.dumps(fact_to_doc_ids[k]),
            provenance_mapping=json.dumps(fact_to_prov_ids[k])
        ))

    session.bulk_insert_mappings(PredicationDenorm, insert_list)
    session.commit()
    insert_list.clear()

    end_time = datetime.now()
    logging.info(f"Done. Took me {end_time - start_time} minutes.")


if __name__ == "__main__":
    main()
