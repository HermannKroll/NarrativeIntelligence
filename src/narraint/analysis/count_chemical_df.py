import argparse
import logging

from datetime import datetime

from narrant.backend.database import Session
from narrant.backend.models import Tag
from narraint.progress import print_progress_with_eta


MIN_DOCS_FOR_ENTITY = 10
MIN_DOCS_FOR_ENT_COMBINATION = 10


def build_index(session, ent_type):
    ent_query = session.query(Tag.document_id, Tag.ent_id)
    ent_query = ent_query.filter(Tag.document_collection == 'PMC')
    ent_query = ent_query.filter(Tag.ent_type == ent_type)
    ent2docs = {}
    for r in session.execute(ent_query):
        doc_id, ent_id = r[0], r[1]

        if ent_id == '':
            continue

        if ent_id not in ent2docs:
            ent2docs[ent_id] = set()
        ent2docs[ent_id].add(doc_id)

    # keep only entities occurring in at least MIN_DOCS_FOR_ENTITY documents
    ent2docs_cleaned = {}
    for ent, docs in ent2docs.items():
        if len(docs) < MIN_DOCS_FOR_ENTITY:
            continue
        ent2docs_cleaned[ent] = docs
    return ent2docs_cleaned


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help='resulting file')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    session = Session.get()
    logging.info("loading 'Chemical' tags from database...")
    chemical2docs = build_index(session, 'Chemical')
    logging.info('{} Chemicals load'.format(len(chemical2docs)))

    logging.info("loading 'DosageForm' tags from database...")
    df2docs = build_index(session, 'DosageForm')
    logging.info('{} DosageForms load'.format(len(df2docs)))

    logging.info('computing chem-df pairs...')
    results = []
    size = len(chemical2docs) * len(df2docs)
    i = 0
    start_time = datetime.now()
    for chem, chem_docs in chemical2docs.items():
        for df, df_docs in df2docs.items():
            i += 1
            print_progress_with_eta('counting', i, size, start_time)

            inter_docs = chem_docs.intersection(df_docs)
            if len(inter_docs) < MIN_DOCS_FOR_ENT_COMBINATION:
                continue
            results.append((chem, df, len(inter_docs)))
    logging.info('writing results to file...')
    with open(args.output, 'w') as f:
        f.write('Chemical\tDosageForm\tDocuments')
        for chem, df, docs in results:
            f.write('\n{}\t{}\t{}'.format(chem, df, docs))

    logging.info('finished')


if __name__ == "__main__":
    main()