import argparse
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import delete, text

from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, DatabaseUpdate, Document
from narraint.backend.models import PredicationInvertedIndex
from narraint.config import BULK_INSERT_AFTER_K, QUERY_YIELD_PER_K

"""
The predication dictionary uses strings instead of tuples as keys ('seen_keys') for predication entries. With this, 
the memory usage is lower.
"""

SEPERATOR_STRING = "_;_"

def insert_data(session, fact_to_doc_ids, newer_documents, insert_list):

    if newer_documents:
        logging.info('Delta Mode activated - Only updating relevant inverted index entries')
        inv_count = session.query(PredicationInvertedIndex).count()
        logging.info(f'{inv_count} entries are in the inverted index')
        inv_q = session.query(PredicationInvertedIndex).yield_per(QUERY_YIELD_PER_K)
        deleted_rows = 0

        p2 = Progress(total=inv_count, print_every=1000, text="Checking existing entries...")
        p2.start_time()
        for idx, row in enumerate(inv_q):
            p2.print_progress(idx)
            row_key = SEPERATOR_STRING.join([str(row.subject_id), str(row.subject_type), str(row.relation),
                                             str(row.object_id), str(row.object_type)])

            # if this key has been updated - we need to retain the old document ids + delete the old entry
            if row_key in fact_to_doc_ids:
                # This works because documents are either new or old (we do not do updates within documents)
                doc_collection = row.document_collection
                old_document_ids = PredicationInvertedIndex.prepare_document_ids(row.document_ids)

                if doc_collection in fact_to_doc_ids[row_key]:
                    fact_to_doc_ids[row_key][doc_collection].update(old_document_ids)
                else:
                    fact_to_doc_ids[row_key][doc_collection] = old_document_ids

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

    # Converting all sets to sorted lists in descending order
    for row_key in fact_to_doc_ids:
        for doc_collection in fact_to_doc_ids[row_key]:
            fact_to_doc_ids[row_key][doc_collection] = sorted(fact_to_doc_ids[row_key][doc_collection], reverse=True)

    key_count = len(fact_to_doc_ids)
    progress2 = Progress(total=key_count, print_every=100, text="insert values...")
    progress2.start_time()
    for idx, row_key in enumerate(fact_to_doc_ids):
        for doc_collection in fact_to_doc_ids[row_key]:
            progress2.print_progress(idx)
            if idx % BULK_INSERT_AFTER_K == 0:
                PredicationInvertedIndex.bulk_insert_values_into_table(session, insert_list, check_constraints=False,
                                                                       commit=False)
                insert_list.clear()

            assert len(fact_to_doc_ids[row_key][doc_collection]) > 0
            subject_id, subject_type, relation, object_id, object_type = row_key.split(SEPERATOR_STRING)
            document_ids_str = "[" + ",".join(str(i) for i in fact_to_doc_ids[row_key][doc_collection]) + "]"
            insert_list.append(dict(
                document_collection=doc_collection,
                subject_id=subject_id,
                subject_type=subject_type,
                relation=relation,
                object_id=object_id,
                object_type=object_type,
                support=len(fact_to_doc_ids[row_key][doc_collection]),
                document_ids=document_ids_str
            ))
    progress2.done()

    PredicationInvertedIndex.bulk_insert_values_into_table(session, insert_list, check_constraints=False, commit=False)
    insert_list.clear()


def denormalize_predication_table(newer_documents: bool = False, low_memory=False, buffer_size=1000):
    if newer_documents and low_memory:
        raise NotImplementedError('Low memory mode and predication id minimum cannot be used together')

    session = SessionExtended.get()
    if not newer_documents:
        logging.info('Deleting old denormalized predication...')
        stmt = delete(PredicationInvertedIndex)
        session.execute(stmt)
        session.commit()

    if SessionExtended.is_postgres:
        session.execute(text("LOCK TABLE " + PredicationInvertedIndex.__tablename__ + " IN EXCLUSIVE MODE"))

    logging.info('Counting the number of predications...')
    pred_count = session.query(Predication).filter(Predication.relation != None)
    if newer_documents:
        latest_update = DatabaseUpdate.get_latest_update(session)
        logging.info(f'Only considering predication ids after {latest_update}')
        pred_count = pred_count.join(Document, isouter=False)
        pred_count = pred_count.filter(Document.date_inserted >= latest_update)
        pred_count = pred_count.filter(Predication.relation != None)
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

    if newer_documents:
        latest_update = DatabaseUpdate.get_latest_update(session)
        prov_query = prov_query.join(Document)
        prov_query = prov_query.filter(Document.date_inserted >= latest_update)
        prov_query = prov_query.filter(Predication.relation != None)

    if low_memory:
        prov_query = prov_query.order_by(Predication.subject_id, Predication.subject_type, Predication.relation,
                                         Predication.object_id, Predication.object_type)

    prov_query = prov_query.yield_per(10 * QUERY_YIELD_PER_K)

    insert_list = []
    logging.info("Starting...")
    fact_to_doc_ids = defaultdict(lambda: defaultdict(set))

    progress = Progress(total=pred_count, print_every=1000, text="denormalizing predication...")
    progress.start_time()

    if low_memory:
        buffer = defaultdict(lambda: defaultdict(set))
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
                insert_data(session, buffer, newer_documents, insert_list)
                buffer.clear()

            last_spo = s_p_o
            seen_key = SEPERATOR_STRING.join([str(s_id), str(s_t), str(p), str(o_id), str(o_t)])
            buffer[seen_key][prov.document_collection].add(prov.document_id)

        insert_data(session, buffer, newer_documents, insert_list)
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
            seen_key = SEPERATOR_STRING.join([str(s_id), str(s_t), str(p), str(o_id), str(o_t)])
            fact_to_doc_ids[seen_key][prov.document_collection].add(prov.document_id)

        insert_data(session, fact_to_doc_ids, newer_documents, insert_list)
        session.commit()

    progress.done()

    end_time = datetime.now()
    logging.info(f"Query table created. Took me {end_time - start_time} minutes.")


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--newer-documents", action="store_true", default=False, required=False,
                        help="Compute reverse index only for newer documents (>= latest database-update-date)")
    parser.add_argument("--low-memory", action="store_true", default=False, required=False, help="Use low-memory mode")
    parser.add_argument("--buffer-size", type=int, default=1000, required=False, help="Buffer size for low-memory mode")
    args = parser.parse_args()

    denormalize_predication_table(newer_documents=args.newer_documents, low_memory=args.low_memory,
                                  buffer_size=args.buffer_size)


if __name__ == "__main__":
    main()
