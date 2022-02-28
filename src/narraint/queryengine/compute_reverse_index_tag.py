import json
import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import delete

from narraint.backend.database import SessionExtended
from narraint.backend.models import Tag, TagInvertedIndex
from narraint.config import QUERY_YIELD_PER_K
from kgextractiontoolbox.progress import Progress


def compute_inverted_index_for_tags():
    start_time = datetime.now()
    session = SessionExtended.get()
    logging.info('Deleting old inverted index for tags...')
    stmt = delete(TagInvertedIndex)
    session.execute(stmt)
    session.commit()

    logging.info('Counting the number of tags...')
    tag_count = session.query(Tag).count()
    logging.info(f'{tag_count} tags found')
    progress = Progress(total=tag_count, print_every=1000, text="Computing inverted tag index...")
    progress.start_time()
    query = session.query(Tag).yield_per(QUERY_YIELD_PER_K)

    index = defaultdict(set)
    for idx, tag_row in enumerate(query):
        progress.print_progress(idx)
        key = (tag_row.ent_id, tag_row.ent_type, tag_row.document_collection)
        doc_id = tag_row.document_id

        index[key].add(doc_id)

    progress.done()

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
    compute_inverted_index_for_tags()


if __name__ == "__main__":
    main()
