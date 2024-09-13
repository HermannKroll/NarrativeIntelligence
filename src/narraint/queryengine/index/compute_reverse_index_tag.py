import argparse
import ast
import json
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import delete, text

from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import Tag, TagInvertedIndex, DatabaseUpdate, Document
from narraint.config import QUERY_YIELD_PER_K
from narrant.entity.entityidtranslator import EntityIDTranslator

"""
The tag-cache dictionary uses strings instead of tuples as keys ('seen_keys') for predication entries. With this, 
the memory usage is lower.
"""

SEPERATOR_STRING = "_;_"


def insert_data(session, index, newer_documents):
    if newer_documents:
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


def compute_inverted_index_for_tags(newer_documents: bool = False):
    start_time = datetime.now()
    session = SessionExtended.get()
    if not newer_documents:
        logging.info('Deleting old inverted index for tags...')
        stmt = delete(TagInvertedIndex)
        session.execute(stmt)
        session.commit()

    if SessionExtended.is_postgres:
        session.execute(text("LOCK TABLE " + TagInvertedIndex.__tablename__))

    logging.info('Counting the number of tags...')
    tag_count = session.query(Tag.document_id, Tag.document_collection, Tag.ent_id, Tag.ent_type)
    if newer_documents:
        latest_update = DatabaseUpdate.get_latest_update(session)
        logging.info(f'Delta Mode activated - Only updating documents newer than {latest_update}')
        tag_count = tag_count.join(Document)
        tag_count = tag_count.filter(Document.date_inserted >= latest_update)
    tag_count = tag_count.distinct()
    tag_count = tag_count.count()
    logging.info(f'{tag_count} tags found')

    progress = Progress(total=tag_count, print_every=1000, text="Computing inverted tag index...")
    progress.start_time()

    query = session.query(Tag.document_id, Tag.document_collection, Tag.ent_id, Tag.ent_type)
    if newer_documents:
        latest_update = DatabaseUpdate.get_latest_update(session)
        logging.info(f'Delta Mode activated - Only updating documents newer than {latest_update}')
        query = query.join(Document)
        query = query.filter(Document.date_inserted >= latest_update)
    query = query.distinct()
    query = query.yield_per(QUERY_YIELD_PER_K)

    logging.info('Using the Gene Resolver to replace gene ids by symbols')
    entityidtranslator = EntityIDTranslator()

    index = defaultdict(set)
    for idx, tag_row in enumerate(query):
        progress.print_progress(idx)
        try:
            translated_id = entityidtranslator.translate_entity_id(tag_row.ent_id, tag_row.ent_type)
        except (KeyError, ValueError):
            continue

        key = SEPERATOR_STRING.join([str(translated_id), str(tag_row.ent_type), str(tag_row.document_collection)])
        index[key].add(tag_row.document_id)

    insert_data(session, index, newer_documents)
    session.commit()

    progress.done()

    end_time = datetime.now()
    logging.info(f"Tag inverted index table created. Took me {end_time - start_time} minutes.")


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--newer-documents", action="store_true", default=False, required=False,
                        help="Compute reverse index only for newer documents (>= latest database-update-date)")
    args = parser.parse_args()

    compute_inverted_index_for_tags(newer_documents=args.newer_documents)


if __name__ == "__main__":
    main()
