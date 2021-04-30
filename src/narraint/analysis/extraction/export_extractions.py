import logging

from sqlalchemy import func

from narrant.backend.database import Session
from narrant.backend.models import Predication, Sentence
from narrant.preprocessing.enttypes import DRUG, GENE

DOCUMENT_COLLECTION = 'PubMed'
EXTRACTIONS_TO_EXPORT = 100


def export_extractions_with_predicate(session, predicate, filename):
    logging.info(f'exporting "{predicate}" extractions...')
    extraction_query = session.query(Predication, Sentence).filter(Predication.sentence_id == Sentence.id)\
        .filter(Predication.document_collection == DOCUMENT_COLLECTION) \
        .filter(Predication.predicate_canonicalized == predicate).\
        filter(Predication.subject_type == GENE).filter(Predication.object_type == DRUG)\
        .order_by(func.random()).limit(EXTRACTIONS_TO_EXPORT)

    # sentence ids to load
    with open(filename, 'wt') as f:
        attributes = ["document_id", "sentence", "subject_str", "subject_id", "subject_type", "predicate",
                      "predicate_canonicalized", "object_str", "object_id", "object_type"]
        f.write('\t'.join(attributes))
        for pred in extraction_query:
            values = [str(pred.Predication.document_id), pred.Sentence.text,
                      pred.Predication.subject_str,  pred.Predication.subject_id, pred.Predication.subject_type,
                      pred.Predication.predicate, pred.Predication.predicate_canonicalized,
                      pred.Predication.object_str, pred.Predication.object_id, pred.Predication.object_type]
            value_str = '\t'.join(values)
            f.write(f'\n{value_str}')





def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    session = Session.get()
    export_extractions_with_predicate(session, "metabolises", "extractions_metabolises.tsv")




if __name__ == "__main__":
    main()