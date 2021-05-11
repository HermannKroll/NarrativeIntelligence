import logging
from collections import defaultdict

from sqlalchemy import func

from narraint.backend.database import SessionExtended
from narraint.backend.models import Tag, Document
from narrant.preprocessing.enttypes import DRUG, PLANT_FAMILY, DOSAGE_FORM, EXCIPIENT

ANNOTATIONS_TO_EXPORT = 50
DOCUMENT_COLLECTION = 'PubMed'
CONTEXT_OFFSET = 50


def export_annotations(session, annotation_query, filename):
    document_ids = set()
    doc2tags = defaultdict(set)
    for t in annotation_query:
        document_ids.add(t.document_id)
        doc2tags[t.document_id].add((t.ent_type, t.ent_id, t.ent_str, t.start, t.end))
    
    doc_query = session.query(Document).filter(Document.collection == DOCUMENT_COLLECTION)\
        .filter(Document.id.in_(document_ids))
    
    doc2content = {} 
    for doc in doc_query:
        content = f'{doc.title} {doc.abstract}'
        doc2content[doc.id] = (doc.title, content)

    with open(filename, 'wt') as f:
        f.write('document_id\ttext\tentity_str\tentity_id\tentity_type')
        for doc_id, tags in doc2tags.items():
            doc_title, doc_content = doc2content[doc_id]
            for t in tags:
                e_type, e_id, e_str, e_start, e_stop = t
                text_start = e_start - CONTEXT_OFFSET
                if text_start < 0:
                    text_start = 0
                text_stop = e_stop + CONTEXT_OFFSET
                if text_stop > len(doc_content):
                    text_stop = len(doc_content) - 1

                if e_start > len(doc_title):
                    e_start = e_start + 1

                text_before_ent = doc_content[text_start:e_start]
                text_ent = f'<<<{doc_content[e_start:e_stop]}>>>'
                text_after_end = doc_content[e_stop:text_stop]
                text_snippit = f'{text_before_ent}{text_ent}{text_after_end}'

                f.write(f'\n{doc_id}\t{text_snippit}\t{e_str}\t{e_id}\t{e_type}')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    
    session = SessionExtended.get()

    logging.info('exporting drug annotations...')
    rand_drug_query = session.query(Tag).filter(Tag.document_collection == DOCUMENT_COLLECTION)\
        .filter(Tag.ent_type == DRUG).order_by(func.random()).limit(ANNOTATIONS_TO_EXPORT)
    export_annotations(session, rand_drug_query, 'annotations_drug.tsv')

    logging.info('exporting plant families...')
    rand_pf_query = session.query(Tag).filter(Tag.document_collection == DOCUMENT_COLLECTION)\
        .filter(Tag.ent_type == PLANT_FAMILY).order_by(func.random()).limit(ANNOTATIONS_TO_EXPORT)
    export_annotations(session, rand_pf_query, 'annotations_plant_family.tsv')

    logging.info('exporting dosage forms...')
    rand_df_query = session.query(Tag).filter(Tag.document_collection == DOCUMENT_COLLECTION) \
        .filter(Tag.ent_type == DOSAGE_FORM).order_by(func.random()).limit(ANNOTATIONS_TO_EXPORT)
    export_annotations(session, rand_df_query, 'annotations_dosage_forms.tsv')

    logging.info('exporting excipients...')
    rand_df_query = session.query(Tag).filter(Tag.document_collection == DOCUMENT_COLLECTION) \
        .filter(Tag.ent_type == EXCIPIENT).order_by(func.random()).limit(ANNOTATIONS_TO_EXPORT)
    export_annotations(session, rand_df_query, 'annotations_excipients.tsv')
    logging.info('Finished')

if __name__ == "__main__":
    main()