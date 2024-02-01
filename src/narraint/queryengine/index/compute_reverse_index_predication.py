import argparse
import json
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import and_, delete, text

from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, DocumentMetadataService
from narraint.backend.models import PredicationInvertedIndex
from narraint.config import BULK_INSERT_AFTER_K, QUERY_YIELD_PER_K
from narraint.queryengine.covid19 import get_document_ids_for_covid19, LIT_COVID_COLLECTION, LONG_COVID_COLLECTION


def insert_data(session, fact_to_prov_ids, predication_id_min, insert_list):

    for row_key in fact_to_prov_ids:
        for doc_collection in fact_to_prov_ids[row_key]:
            for docid2prov in fact_to_prov_ids[row_key][doc_collection]:
                fact_to_prov_ids[row_key][doc_collection][docid2prov] = set(fact_to_prov_ids[row_key][doc_collection][docid2prov])

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
                doc_collection = row.document_collection
                for doc_id, predication_ids in json.loads(row.provenance_mapping).items():
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
        if SessionExtended.is_postgres:
            session.execute(text("LOCK TABLE " + PredicationInvertedIndex.__tablename__ + " IN EXCLUSIVE MODE"))

        logging.info('Entries deleted')

    logging.info("Compute insert...")

    # Converting all sets to lists again
    for row_key in fact_to_prov_ids:
        for doc_collection in fact_to_prov_ids[row_key]:
            for docid2prov in fact_to_prov_ids[row_key][doc_collection]:
                fact_to_prov_ids[row_key][doc_collection][docid2prov] = sorted(set(fact_to_prov_ids[row_key][doc_collection][docid2prov]))

    key_count = len(fact_to_prov_ids)
    progress2 = Progress(total=key_count, print_every=100, text="insert values...")
    progress2.start_time()
    for idx, row_key in enumerate(fact_to_prov_ids):
        for doc_collection in fact_to_prov_ids[row_key]:
            progress2.print_progress(idx)
            if idx % BULK_INSERT_AFTER_K == 0:
                PredicationInvertedIndex.bulk_insert_values_into_table(session, insert_list, check_constraints=False, commit=False)
                insert_list.clear()

            assert len(fact_to_prov_ids[row_key][doc_collection]) > 0

            insert_list.append(dict(
                document_collection=doc_collection,
                subject_id=row_key[0],
                subject_type=row_key[1],
                relation=row_key[2],
                object_id=row_key[3],
                object_type=row_key[4],
                support=len(fact_to_prov_ids[row_key][doc_collection]),
                provenance_mapping=json.dumps(fact_to_prov_ids[row_key][doc_collection])
            ))
    progress2.done()

    PredicationInvertedIndex.bulk_insert_values_into_table(session, insert_list, check_constraints=False, commit=False)
    insert_list.clear()


def denormalize_predication_table(predication_id_min: int = None, consider_metadata=True, low_memory=False, buffer_size=1000):
    if predication_id_min and low_memory:
        raise NotImplementedError('Low memory mode and predication id minimum cannot be used together')

    session = SessionExtended.get()
    if not predication_id_min:
        logging.info('Deleting old denormalized predication...')
        stmt = delete(PredicationInvertedIndex)
        session.execute(stmt)
        session.commit()

    if SessionExtended.is_postgres:
        session.execute(text("LOCK TABLE " + PredicationInvertedIndex.__tablename__ + " IN EXCLUSIVE MODE"))

    logging.info('Counting the number of predications...')
    pred_count = session.query(Predication).filter(Predication.relation != None)
    if predication_id_min:
        logging.info(f'Only considering predication ids above {predication_id_min}')
        pred_count = pred_count.filter(Predication.id >= predication_id_min)
    pred_count = pred_count.count()
    logging.info(f'{pred_count} predication were found')

    start_time = datetime.now()
    # "is not None" instead of "!=" None" DOES NOT WORK!
    prov_query = session.query(Predication.id,
                               Predication.document_id, Predication.document_collection,
                               Predication.subject_id, Predication.subject_type,
                               Predication.relation,
                               Predication.object_id, Predication.object_type)

    prov_query = prov_query.filter(Predication.relation != None)

    if consider_metadata:
        logging.info('Only documents are considered that have metadata')
        prov_query = prov_query.join(DocumentMetadataService,
                                     and_(Predication.document_id == DocumentMetadataService.document_id,
                                          Predication.document_collection == DocumentMetadataService.document_collection))
    else:
        logging.info('All documents are considered')
    if predication_id_min:
        prov_query = prov_query.filter(Predication.id >= predication_id_min)

    if low_memory:
        prov_query = prov_query.order_by(Predication.subject_id, Predication.relation, Predication.object_id)

    prov_query = prov_query.yield_per(10 * QUERY_YIELD_PER_K)

    # Hack to support also the Covid 19 collection
    # TODO: not very generic
    doc_ids_litcovid, doc_ids_longcovid = get_document_ids_for_covid19()

    insert_list = []
    logging.info("Starting...")
    fact_to_prov_ids = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))

    progress = Progress(total=pred_count, print_every=1000, text="denormalizing predication...")
    progress.start_time()

    if low_memory:
        buffer = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        last_spo = ()
        for idx, prov in enumerate(prov_query):
            progress.print_progress(idx)
            s_id = prov.subject_id
            s_t = prov.subject_type
            p = prov.relation
            o_id = prov.object_id
            o_t = prov.object_type

            s_p_o = (s_id, p, o_id)
            if idx == 0:
                last_spo = s_p_o
            # The whole spo key must be inserted within one buffer
            if last_spo != s_p_o and len(buffer) >= buffer_size:
                insert_data(session, buffer, predication_id_min, insert_list)
                buffer.clear()

            last_spo = s_p_o
            seen_key = (s_id, s_t, p, o_id, o_t)
            buffer[seen_key][prov.document_collection][prov.document_id].add(prov.id)

            # Hack to support also the Covid 19 collection
            # TODO: not very generic
            if prov.document_collection == "PubMed" and prov.document_id in doc_ids_litcovid:
                buffer[seen_key][LIT_COVID_COLLECTION][prov.document_id].add(prov.id)
            if prov.document_collection == "PubMed" and prov.document_id in doc_ids_longcovid:
                buffer[seen_key][LONG_COVID_COLLECTION][prov.document_id].add(prov.id)

        insert_data(session, buffer, predication_id_min, insert_list)
        session.commit()
        buffer.clear()
    else:
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
                fact_to_prov_ids[seen_key][LIT_COVID_COLLECTION][prov.document_id].add(prov.id)
            if prov.document_collection == "PubMed" and prov.document_id in doc_ids_longcovid:
                fact_to_prov_ids[seen_key][LONG_COVID_COLLECTION][prov.document_id].add(prov.id)

        insert_data(session, fact_to_prov_ids, predication_id_min, insert_list)
        session.commit()

    progress.done()



    end_time = datetime.now()
    logging.info(f"Query table created. Took me {end_time - start_time} minutes.")


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--predicate_id_minimum", default=None, type=int, required=False,
                        help="only predication ids above this will be considered")
    parser.add_argument("--low-memory", action="store_true", default=False, required=False, help="Use low-memory mode")
    parser.add_argument("--buffer-size", type=int, default=1000, required=False, help="Buffer size for low-memory mode")
    parser.add_argument("--ignore-metadata", action="store_true", default=False, required=False, help="By default only documents are indexed that have metadata")
    args = parser.parse_args()

    denormalize_predication_table(predication_id_min=args.predicate_id_minimum, low_memory=args.low_memory, buffer_size=args.buffer_size,
                                  consider_metadata=not args.ignore_metadata)


if __name__ == "__main__":
    main()
