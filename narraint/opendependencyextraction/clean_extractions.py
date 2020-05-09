import argparse
import logging
from operator import or_, and_

from narraint.backend.database import Session
from narraint.backend.models import Predication
from narraint.entity.enttypes import CHEMICAL, DISEASE
from narraint.openie.canonicalize_predicates import PRED_TO_REMOVE


def clean_extractions_in_database(document_collection):
    session = Session.get()

    # Delete all treatments which are not (Chemical -> Disease)
    logging.info('Cleaning treats (Chemical -> Disease)...')
    q_treatment = session.query(Predication).filter(and_(Predication.document_collection == document_collection,
                                                         and_(Predication.predicate_canonicalized == 'treats',
                                                    or_(Predication.subject_type != CHEMICAL,
                                                        Predication.object_type != DISEASE))))
    q_treatment.delete()
    session.commit()

    logging.info('Cleaning decreases (Chemical -> ...)')
    q_decrease = session.query(Predication).filter(and_(Predication.document_collection == document_collection,
                                                        and_(Predication.predicate_canonicalized == 'decreases',
                                                        Predication.subject_type != CHEMICAL)))
    q_decrease.delete()
    session.commit()

    logging.info('Cleaning causes (Chemical -> ...)')
    q_cause = session.query(Predication).filter(and_(Predication.document_collection == document_collection,
                                                     and_(Predication.predicate_canonicalized == 'causes',
        or_(Predication.object_type != DISEASE, and_(Predication.subject_type != CHEMICAL,
                                                     Predication.subject_type != DISEASE)))))
    q_cause.delete()
    session.commit()

    logging.info('Cleaning predicate to remove ...')
    q_to_remove = session.query(Predication).filter(and_(Predication.document_collection == document_collection,
                                           Predication.predicate_canonicalized == "PRED_TO_REMOVE"))
    q_to_remove.delete()
    session.commit()



def main():
    """
    Input: Directory with Pubtator files
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--collection", required=True, help='collection to which the ids belong')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    logging.info('Cleaning database (collection = {})...'.format(args.collection))
    clean_extractions_in_database(args.collection)
    logging.info('finished')


if __name__ == "__main__":
    main()