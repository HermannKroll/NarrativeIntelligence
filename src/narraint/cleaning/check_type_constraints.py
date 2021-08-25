import argparse
import logging
from datetime import datetime

from sqlalchemy import delete

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, PredicationToDelete
from narraint.cleaning.relation_type_constraints import RelationTypeConstraintStore
from narrant.progress import print_progress_with_eta

BULK_QUERY_CURSOR_COUNT = 100000


def clean_predication_to_delete_table(session):
    """
    Clean all entries in the PredicationToDelete table
    :param session: the current session
    :return: None
    """
    logging.debug('Cleaning Predication To Delete Table...')
    stmt = delete(PredicationToDelete)
    session.execute(stmt)
    logging.debug('Committing...')
    session.commit()


def delete_predications_hurting_type_constraints(relation_type_constraints: RelationTypeConstraintStore,
                                                 document_collection: str = None):
    """
    Checks the type constraints
    If subject and object could be swapped to meet the constraint - they will be swapped
    Otherwise the extraction will be mapped to associate
    :param relation_type_constraints: the relation type constraint store
    :param document_collection: apply constraints only for this document collection
    :return: None
    """
    preds_to_delete = set()
    session = SessionExtended.get()
    clean_predication_to_delete_table(session)
    logging.info('Counting the number of predications...')
    if document_collection:
        pred_count = session.query(Predication).filter(Predication.document_collection == document_collection).count()
    else:
        pred_count = session.query(Predication).count()
    logging.info(f'{pred_count} predications were found')
    logging.info('Querying predications...')
    if document_collection:
        pred_query = session.query(Predication) \
            .filter(Predication.relation != None) \
            .filter(Predication.document_collection == document_collection) \
            .yield_per(BULK_QUERY_CURSOR_COUNT)
    else:
        pred_query = session.query(Predication).filter(Predication.relation != None) \
            .yield_per(BULK_QUERY_CURSOR_COUNT)
    start_time = datetime.now()
    for idx, pred in enumerate(pred_query):
        print_progress_with_eta("checking type constraints", idx, pred_count, start_time)
        if pred.relation in relation_type_constraints.constraints:
            s_types = relation_type_constraints.get_subject_constraints(pred.relation)
            o_types = relation_type_constraints.get_object_constraints(pred.relation)
            if pred.subject_type not in s_types or pred.object_type not in o_types:
                # arguments hurt type constraints
                preds_to_delete.add(pred.id)

    logging.info(f'Deleting {len(preds_to_delete)} predications...')
    values_to_delete = []
    for id_to_delete in preds_to_delete:
        values_to_delete.append(dict(predication_id=id_to_delete))
    PredicationToDelete.bulk_insert_values_into_table(session, values_to_delete)
    subquery = session.query(PredicationToDelete.predication_id).subquery()
    stmt = delete(Predication).where(Predication.id.in_(subquery))
    session.execute(stmt)
    logging.debug('Committing...')
    session.commit()
    clean_predication_to_delete_table(session)


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("constraint_file", help='Path to the relation constraint JSON file')
    parser.add_argument("-c", "--collection", required=False, help='Apply constraints only in this document collection')

    args = parser.parse_args()
    constraints = RelationTypeConstraintStore()
    logging.info(f'Loading constraints from {args.constraint_file}')
    constraints.load_from_json(args.constraint_file)
    logging.info('Checking type constraints...')
    delete_predications_hurting_type_constraints(constraints, document_collection=args.collection)
    logging.info('Finished...')


if __name__ == "__main__":
    main()
