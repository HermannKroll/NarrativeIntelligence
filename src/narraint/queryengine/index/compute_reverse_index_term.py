import itertools
import logging
import string
from datetime import datetime

import nltk
from sqlalchemy import delete, text

from kgextractiontoolbox.backend.models import Document
from kgextractiontoolbox.backend.retrieve import iterate_over_all_documents_in_collection
from kgextractiontoolbox.progress import Progress
from narraint.backend.database import SessionExtended
from narraint.backend.models import TermInvertedIndex


def compute_inverted_index_for_terms():
    start_time = datetime.now()
    session = SessionExtended.get()
    logging.info('Deleting old inverted index for terms...')
    stmt = delete(TermInvertedIndex)
    session.execute(stmt)
    session.commit()

    if SessionExtended.is_postgres:
        session.execute(text("LOCK TABLE " + TermInvertedIndex.__tablename__))

    stopwords = set(nltk.corpus.stopwords.words('english'))
    trans_map = {p: ' ' for p in string.punctuation}
    translator = str.maketrans(trans_map)
    logging.info('Creating term index...')

    # get all document collections
    logging.info('Computing document collections...')
    document_collections = set([r[0] for r in session.query(Document.collection).distinct()])
    logging.info(f'Iterate over the following collections: {document_collections}')
    for collection in document_collections:
        logging.info(f'Counting documents of {collection} in database...')
        # iterate over all extracted statements
        total = session.query(Document).filter(Document.collection == collection).count()
        progress = Progress(total=total, print_every=1000, text="Computing term index...")
        progress.start_time()
        term_index_local = {}
        for i, doc in enumerate(iterate_over_all_documents_in_collection(session=session, collection=collection)):
            progress.print_progress(i)
            # Make it lower + replace all punctuation by ' '
            doc_text = doc.get_text_content().strip().lower()
            # To this with and without punctuation removal
            doc_text_without_punctuation = doc_text.translate(translator)
            for term in itertools.chain(doc_text.split(' '), doc_text_without_punctuation.split(' ')):
                term = term.strip()
                if not term or term in stopwords:
                    continue
                if term not in term_index_local:
                    term_index_local[term] = set()

                term_index_local[term].add(doc.id)

        progress.done()
        logging.info('Preparing insert data...')
        insert_list = []
        for term, doc_ids in term_index_local.items():
            insert_list.append(dict(term=term,
                                    document_collection=collection,
                                    document_ids=str(doc_ids), reverse=True))

        logging.info('Beginning insert into term_inverted_index table...')
        TermInvertedIndex.bulk_insert_values_into_table(session, insert_list, check_constraints=True, commit=False)
        insert_list.clear()

    session.commit()
    end_time = datetime.now()
    logging.info(f"Term inverted index table created. Took me {end_time - start_time} minutes.")


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    compute_inverted_index_for_terms()


if __name__ == "__main__":
    main()
