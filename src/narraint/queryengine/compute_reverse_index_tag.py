import argparse
import json
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import delete, and_

from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import Tag, TagInvertedIndex, Predication
from narraint.config import QUERY_YIELD_PER_K


def compute_inverted_index_for_tags(predication_id_min: int = None):
    start_time = datetime.now()
    session = SessionExtended.get()
    if not predication_id_min:
        logging.info('Deleting old inverted index for tags...')
        stmt = delete(TagInvertedIndex)
        session.execute(stmt)
        session.commit()

    logging.info('Counting the number of tags...')
    tag_count = session.query(Tag)

    if predication_id_min:
        logging.info('Delta Mode activated - Only updating relevant inverted index entries')
        tag_count.join(Predication).filter(Predication.id >= predication_id_min)
        tag_count = tag_count.filter(and_(Tag.document_id == Predication.document_id,
                                          Tag.document_collection == Predication.document_collection))

    tag_count = tag_count.count()

    logging.info(f'{tag_count} tags found')
    progress = Progress(total=tag_count, print_every=1000, text="Computing inverted tag index...")
    progress.start_time()
    query = session.query(Tag)

    if predication_id_min:
        query.join(Predication).filter(Predication.id >= predication_id_min)
        query = query.filter(and_(Tag.document_id == Predication.document_id,
                                  Tag.document_collection == Predication.document_collection))

    query = query.yield_per(QUERY_YIELD_PER_K)

    index = defaultdict(set)
    for idx, tag_row in enumerate(query):
        progress.print_progress(idx)
        key = (tag_row.ent_id, tag_row.ent_type, tag_row.document_collection)
        doc_id = tag_row.document_id

        index[key].add(doc_id)

    progress.done()

    if predication_id_min:
        logging.info('Delta Mode activated - Only updating relevant inverted index entries')
        inv_q = session.query(TagInvertedIndex).yield_per(QUERY_YIELD_PER_K)
        deleted_rows = 0
        for idx, row in enumerate(inv_q):
            row_key = row.entity_id, row.entity_type, row.document_collection

            # if this key has been updated - we need to retain the old document ids + delete the old entry
            if row_key in index:
                index[row_key].update([int(doc_id) for doc_id in json.loads(row.document_ids)])
                deleted_rows += 1
                session.delete(row)

        logging.info(f'{deleted_rows} inverted index entries must be deleted')
        logging.debug('Committing...')
        session.commit()
        logging.info('Entries deleted')

    progress = Progress(total=len(index.items()), print_every=1000, text="Computing insert values...")
    progress.start_time()
    insert_list = []
    for (entity_id, entity_type, doc_col), doc_ids in index.items():
        insert_list.append(dict(entity_id=entity_id,
                                entity_type=entity_type,
                                document_collection=doc_col,
                                document_ids=json.dumps(sorted(list(doc_ids), reverse=True))))
    progress.done()

    logging.info('Beginning insert into tag_inverted_index table...')
    TagInvertedIndex.bulk_insert_values_into_table(session, insert_list, check_constraints=True)
    insert_list.clear()

    end_time = datetime.now()
    logging.info(f"Tag inverted index table created. Took me {end_time - start_time} minutes.")


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--predicate_id_minimum", default=None, type=int, required=False,
                        help="only predication ids above this will be considered")
    args = parser.parse_args()

    compute_inverted_index_for_tags(predication_id_min=args.predicate_id_minimum)


if __name__ == "__main__":
    main()
