import argparse
import json
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import and_, delete

from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, DocumentMetadataService
from narraint.backend.models import PredicationInvertedIndex
from narraint.config import BULK_INSERT_AFTER_K, QUERY_YIELD_PER_K
from narraint.queryengine.covid19 import get_document_ids_for_covid19, LIT_COVID_COLLECTION, LONG_COVID_COLLECTION


def denormalize_predication_table(predication_id_min: int = None, consider_metadata=True):
    session = SessionExtended.get()
    if not predication_id_min:
        logging.info('Deleting old denormalized predication...')
        stmt = delete(PredicationInvertedIndex)
        session.execute(stmt)
        session.commit()

    logging.info('Counting the number of predications...')
    pred_count = session.query(Predication).filter(Predication.relation != None)
    if predication_id_min:
        logging.info(f'Only considering predication ids above {predication_id_min}')
        pred_count = pred_count.filter(Predication.id > predication_id_min)
    pred_count = pred_count.count()

    start_time = datetime.now()
    # "is not None" instead of "!=" None" DOES NOT WORK!
    prov_query = session.query(Predication).filter(Predication.relation != None)

    if consider_metadata:
        prov_query = prov_query.join(DocumentMetadataService,
                                     and_(Predication.document_id == DocumentMetadataService.document_id,
                                          Predication.document_collection == DocumentMetadataService.document_collection))
    if predication_id_min:
        prov_query = prov_query.filter(Predication.id >= predication_id_min)

    prov_query = prov_query.yield_per(QUERY_YIELD_PER_K)

    # Hack to support also the Covid 19 collection
    # TODO: not very generic
    doc_ids_litcovid, doc_ids_longcovid = get_document_ids_for_covid19()

    insert_list = []
    logging.info("Starting...")
    # fact_to_doc_ids = defaultdict(lambda: defaultdict(list))
    fact_to_prov_ids = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

    progress = Progress(total=pred_count, print_every=1000, text="denormalizing predication...")
    progress.start_time()
    for idx, prov in enumerate(prov_query):
        progress.print_progress(idx)
        s_id = prov.subject_id
        s_t = prov.subject_type
        p = prov.relation
        o_id = prov.object_id
        o_t = prov.object_type
        seen_key = (s_id, s_t, p, o_id, o_t)
        # fact_to_doc_ids[seen_key][prov.document_collection].append(prov.document_id)
        fact_to_prov_ids[seen_key][prov.document_collection][prov.document_id].add(prov.id)

        # Hack to support also the Covid 19 collection
        # TODO: not very generic
        if prov.document_collection == "PubMed" and prov.document_id in doc_ids_litcovid:
            #    fact_to_doc_ids[seen_key][LIT_COVID_COLLECTION].append(prov.document_id)
            fact_to_prov_ids[seen_key][LIT_COVID_COLLECTION][prov.document_id].add(prov.id)
        if prov.document_collection == "PubMed" and prov.document_id in doc_ids_longcovid:
            #   fact_to_doc_ids[seen_key][LONG_COVID_COLLECTION].append(prov.document_id)
            fact_to_prov_ids[seen_key][LONG_COVID_COLLECTION][prov.document_id].add(prov.id)

    progress.done()

    # Restructure dictionaries
    # for k in fact_to_doc_ids:
    #   for v in fact_to_doc_ids[k]:
    #      fact_to_doc_ids[k][v] = sorted(set(fact_to_doc_ids[k][v]))

    for k in fact_to_prov_ids:
        for v in fact_to_prov_ids[k]:
            for w in fact_to_prov_ids[k][v]:
                fact_to_prov_ids[k][v][w] = set(fact_to_prov_ids[k][v][w])

    if predication_id_min:
        logging.info('Delta Mode activated - Only updating relevant inverted index entries')
        inv_count = session.query(PredicationInvertedIndex).count()
        logging.info(f'{inv_count} entries are in the inverted index')
        inv_q = session.query(PredicationInvertedIndex).yield_per(QUERY_YIELD_PER_K)
        deleted_rows = 0

        p2 = Progress(total=inv_count, print_every=1000, text="Checking existing entries...")
        p2.start_time()
        for idx, row in enumerate(inv_q):
            p2.print_progress(idx)
            row_key = row.subject_id, row.subject_type, row.relation, row.object_id, row.object_type

            # if this key has been updated - we need to retain the old document ids + delete the old entry
            if row_key in fact_to_prov_ids:
                # This works because documents are either new or old (we do not do updates within documents)
                for doc_collection, provs in json.loads(row.provenance_mapping).items():
                    for doc_id, predication_ids in provs.items():
                        doc_id = int(doc_id)
                        if doc_id in fact_to_prov_ids[row_key][doc_collection]:
                            fact_to_prov_ids[row_key][doc_collection][doc_id].update(predication_ids)
                        else:
                            fact_to_prov_ids[row_key][doc_collection][doc_id] = predication_ids

                session.delete(row)
                deleted_rows += 1

        p2.done()
        logging.info(f'{deleted_rows} inverted index entries must be deleted')
        logging.debug('Committing...')
        session.commit()
        logging.info('Entries deleted')

    logging.info("Compute insert...")

    # Converting all sets to lists again
    for k in fact_to_prov_ids:
        for v in fact_to_prov_ids[k]:
            for w in fact_to_prov_ids[k][v]:
                fact_to_prov_ids[k][v][w] = sorted(set(fact_to_prov_ids[k][v][w]))

    key_count = len(fact_to_prov_ids)
    progress2 = Progress(total=key_count, print_every=100, text="insert values...")
    progress2.start_time()
    for idx, k in enumerate(fact_to_prov_ids):
        progress2.print_progress(idx)
        if idx % BULK_INSERT_AFTER_K == 0:
            PredicationInvertedIndex.bulk_insert_values_into_table(session, insert_list, check_constraints=False)
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
    progress2.done()

    PredicationInvertedIndex.bulk_insert_values_into_table(session, insert_list, check_constraints=False)
    insert_list.clear()

    end_time = datetime.now()
    logging.info(f"Query table created. Took me {end_time - start_time} minutes.")


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--predicate_id_minimum", default=None, type=int, required=False,
                        help="only predication ids above this will be considered")
    args = parser.parse_args()

    denormalize_predication_table(predication_id_min=args.predicate_id_minimum)


if __name__ == "__main__":
    main()
