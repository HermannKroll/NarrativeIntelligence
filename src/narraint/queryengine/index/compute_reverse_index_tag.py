import argparse
import ast
import json
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import delete, text

from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import Tag, TagInvertedIndex, Predication
from narraint.config import QUERY_YIELD_PER_K
from narrant.entity.entityidtranslator import EntityIDTranslator

"""
The tag-cache dictionary uses strings instead of tuples as keys ('seen_keys') for predication entries. With this, 
the memory usage is lower.
"""

SEPERATOR_STRING = "_;_"


def insert_data(session, index, predication_id_min):
    if predication_id_min:
        logging.info('Delta Mode activated - Only updating relevant inverted index entries')
        inv_count = session.query(TagInvertedIndex).count()
        logging.info(f'{inv_count} entries in index found')
        inv_q = session.query(TagInvertedIndex).yield_per(QUERY_YIELD_PER_K)
        p2 = Progress(total=inv_count, print_every=1000, text="Checking existing entries...")
        p2.start_time()
        deleted_rows = 0
        for idx, row in enumerate(inv_q):
            p2.print_progress(idx)
            # tag ids are already translated inside the TagInvertedIndex
            row_key = SEPERATOR_STRING.join([str(row.entity_id), str(row.entity_type), str(row.document_collection)])

            # if this key has been updated - we need to retain the old document ids + delete the old entry
            if row_key in index:
                index[row_key].update([int(doc_id) for doc_id in ast.literal_eval(row.document_ids)])
                deleted_rows += 1
                session.delete(row)
        p2.done()
        logging.info(f'{deleted_rows} inverted index entries must be deleted')

        logging.debug('Committing...')
        session.commit()

        if SessionExtended.is_postgres:
            session.execute(text("LOCK TABLE " + TagInvertedIndex.__tablename__))

        logging.info('Entries deleted')

    progress = Progress(total=len(index.items()), print_every=1000, text="Computing insert values...")
    progress.start_time()
    insert_list = []
    for row_key, doc_ids in index.items():
        entity_id, entity_type, doc_col = row_key.split(SEPERATOR_STRING)
        insert_list.append(dict(entity_id=entity_id,
                                entity_type=entity_type,
                                document_collection=doc_col,
                                support=len(doc_ids),
                                document_ids=json.dumps(sorted(list(doc_ids), reverse=True))))
    progress.done()
    logging.info('Beginning insert into tag_inverted_index table...')
    TagInvertedIndex.bulk_insert_values_into_table(session, insert_list, check_constraints=True, commit=False)
    insert_list.clear()


def compute_inverted_index_for_tags(predication_id_min: int = None, low_memory=False, buffer_size=1000):
    if predication_id_min and low_memory:
        raise NotImplementedError('Low memory mode and predication id minimum cannot be used together')

    start_time = datetime.now()
    session = SessionExtended.get()
    if not predication_id_min:
        logging.info('Deleting old inverted index for tags...')
        stmt = delete(TagInvertedIndex)
        session.execute(stmt)
        session.commit()

    if SessionExtended.is_postgres:
        session.execute(text("LOCK TABLE " + TagInvertedIndex.__tablename__))

    logging.info('Counting the number of tags...')
    tag_count = session.query(Tag.document_id, Tag.document_collection, Tag.ent_id, Tag.ent_type)
    tag_count = tag_count.distinct()
    tag_count = tag_count.count()
    logging.info(f'{tag_count} tags found')

    collection2doc_ids = defaultdict(set)
    if predication_id_min:
        logging.info(
            f'Delta Mode activated - Only updating relevant inverted index entries (id >= {predication_id_min})')
        doc_id_query = session.query(Predication.document_id, Predication.document_collection)
        doc_id_query = doc_id_query.filter(Predication.id >= predication_id_min)
        doc_id_query = doc_id_query.distinct()
        count = 0
        for row in doc_id_query:
            collection2doc_ids[row.document_collection].add(int(row.document_id))
            count += 1
        logging.info(f'{count} document ids for {len(collection2doc_ids)} collections found...')

    progress = Progress(total=tag_count, print_every=1000, text="Computing inverted tag index...")
    progress.start_time()

    query = session.query(Tag.document_id, Tag.document_collection, Tag.ent_id, Tag.ent_type)
    query = query.distinct()
    if low_memory:
        query = query.order_by(Tag.ent_id, Tag.ent_type, Tag.document_collection, Tag.document_id)
    query = query.yield_per(QUERY_YIELD_PER_K)

    logging.info('Using the Gene Resolver to replace gene ids by symbols')
    entityidtranslator = EntityIDTranslator()

    if low_memory:
        buffer = defaultdict(set)
        last_key = ()
        for idx, tag_row in enumerate(query):
            progress.print_progress(idx)
            try:
                translated_id = entityidtranslator.translate_entity_id(tag_row.ent_id, tag_row.ent_type)
            except (KeyError, ValueError):
                continue

            sort_key = (tag_row.document_collection, translated_id, tag_row.ent_type)
            if idx == 0:
                last_key = sort_key

            # The whole tag must be inserted within one buffer
            if last_key != sort_key and len(buffer) >= buffer_size:
                insert_data(session, buffer, predication_id_min)
                buffer.clear()

            last_key = sort_key
            key = SEPERATOR_STRING.join([str(translated_id), str(tag_row.ent_type), str(tag_row.document_collection)])
            buffer[key].add(tag_row.document_id)

        insert_data(session, buffer, predication_id_min)
        session.commit()
        buffer.clear()

    else:
        index = defaultdict(set)
        for idx, tag_row in enumerate(query):
            progress.print_progress(idx)
            if predication_id_min and tag_row.document_id not in collection2doc_ids[tag_row.document_collection]:
                continue
            try:
                translated_id = entityidtranslator.translate_entity_id(tag_row.ent_id, tag_row.ent_type)
            except (KeyError, ValueError):
                continue

            key = SEPERATOR_STRING.join([str(translated_id), str(tag_row.ent_type), str(tag_row.document_collection)])
            index[key].add(tag_row.document_id)

        insert_data(session, index, predication_id_min)
        session.commit()

    progress.done()

    end_time = datetime.now()
    logging.info(f"Tag inverted index table created. Took me {end_time - start_time} minutes.")


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--predicate_id_minimum", default=None, type=int, required=False,
                        help="only predication ids above this will be considered")
    parser.add_argument("--low-memory", action="store_true", default=False, required=False, help="Use low-memory mode")
    parser.add_argument("--buffer-size", type=int, default=1000, required=False, help="Buffer size for low-memory mode")
    args = parser.parse_args()

    compute_inverted_index_for_tags(predication_id_min=args.predicate_id_minimum, low_memory=args.low_memory,
                                    buffer_size=args.buffer_size)


if __name__ == "__main__":
    main()
