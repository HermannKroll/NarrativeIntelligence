import logging
from collections import defaultdict
from datetime import datetime
from io import StringIO

from sqlalchemy import update, or_, delete

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, PredicationToDelete, Sentence
from narraint.cleaning.relation_vocabulary import DOSAGE_FORM_PREDICATE, METHOD_PREDICATE, \
    ASSOCIATED_PREDICATE_UNSURE
from narraint.queryengine.query_hints import sort_symmetric_arguments, SYMMETRIC_PREDICATES, PREDICATE_TYPING, \
    are_subject_and_object_correctly_ordered
from narrant.backend.database import Session
from narrant.preprocessing.enttypes import DOSAGE_FORM, LAB_METHOD, METHOD
from narrant.progress import print_progress_with_eta

BULK_INSERT_PRED_TO_DELETE_AFTER_K = 1000000
BULK_QUERY_CURSOR_COUNT = 100000


def clean_predication_to_delete_table(session):
    """
    Clean all entries in the PredicationToDelete table
    :param session: the current session
    :return: None
    """
    logging.info('Cleaning Predication To Delete Table...')
    stmt = delete(PredicationToDelete)
    session.execute(stmt)
    logging.debug('Committing...')
    session.commit()


def insert_predication_ids_to_delete(predication_ids: [int]):
    """
    Insert a list of predication ids into a the PredicationToDelete table
    :param predication_ids: a list of integers
    :return: None
    """
    session = SessionExtended.get()
    start_time = datetime.now()
    if Session.is_postgres:
        logging.debug('Using fast postgres copy mode...')
        f_pred_to_delete = StringIO()
        preds2delete_list = sorted(predication_ids)
        for idx, pred_id in enumerate(preds2delete_list):
            print_progress_with_eta("writing to temp file...", idx, len(predication_ids), start_time)
            if idx == 0:
                f_pred_to_delete.write(str(pred_id))
            else:
                f_pred_to_delete.write(f'\n{pred_id}')

        pred_to_delete_keys = ["predication_id"]
        logging.debug('Executing copy from temp file to predication_to_delete ...')
        connection = session.connection().connection
        cursor = connection.cursor()
        f_pred_to_delete.seek(0)
        cursor.copy_from(f_pred_to_delete, 'predication_to_delete', sep='\t', columns=pred_to_delete_keys)
        logging.debug('Committing...')
        connection.commit()
    else:
        logging.debug('Using slower bulk insert...')
        pred_to_delete_task = []
        for idx, pred_id in enumerate(predication_ids):
            pred_to_delete_task.append(dict(predication_id=pred_id))
            if idx > 0 and idx % BULK_INSERT_PRED_TO_DELETE_AFTER_K == 0:
                session.bulk_insert_mappings(PredicationToDelete, pred_to_delete_task)
                session.commit()
                pred_to_delete_task.clear()
            print_progress_with_eta("Inserting predication ids to delete", idx, len(predication_ids), start_time)
        session.bulk_insert_mappings(PredicationToDelete, pred_to_delete_task)
        session.commit()
        pred_to_delete_task.clear()

    logging.debug(f'{len(predication_ids)} ids have been inserted')


def clean_redundant_predicate_tuples(session, symmetric_relation: str):
    logging.info('Counting predication...')
    predication_count = Predication.query_predication_count(session, symmetric_relation)
    logging.info('Querying relevant predication entries...')
    query = session.query(Predication.id, Predication.sentence_id,
                          Predication.subject_id, Predication.subject_type,
                          Predication.predicate,
                          Predication.object_id, Predication.object_type) \
        .filter(Predication.relation == symmetric_relation)

    sentence2pred = defaultdict(set)
    preds2delete = set()
    start_time = datetime.now()
    logging.info('Computing duplicated values...')
    for idx, row in enumerate(session.execute(query)):
        p_id, sent_id, subj_id, subj_type, predicate, obj_id, obj_type = int(row[0]), int(row[1]), row[2], row[3], row[
            4], row[5], row[6]

        # symmetric relation - delete one direction
        sorted_arguments = sort_symmetric_arguments(subj_id, subj_type, obj_id, obj_type)
        if sorted_arguments[0] == subj_id:  # are the arguments sorted correctly?
            key = sorted_arguments[0], sorted_arguments[1], predicate, sorted_arguments[2], sorted_arguments[3]
            # yes - does the fact exists multiple times?
            if key not in sentence2pred[sent_id]:
                # no - everything is fine
                sentence2pred[sent_id].add(key)
            else:
                # predication is duplicated, can be deleted
                preds2delete.add(p_id)
        else:
            # arguments are not in the correct order
            preds2delete.add(p_id)

        print_progress_with_eta(f"computing duplicated {symmetric_relation} values...",
                                idx, predication_count, start_time)

    if predication_count > 0:
        percentage = len(preds2delete) / predication_count
    else:
        percentage = 0
    logging.info(f'Delete {len(preds2delete)} of {predication_count} ({percentage})')
    insert_predication_ids_to_delete(preds2delete)


def clean_redundant_symmetric_predicates():
    session = SessionExtended.get()
    clean_predication_to_delete_table(session)

    logging.info(f'Cleaning the following predicates: {SYMMETRIC_PREDICATES}')
    for predicate in SYMMETRIC_PREDICATES:
        logging.info(f'Cleaning {predicate} entries...')
        clean_redundant_predicate_tuples(session, predicate)

    logging.info('Deleting all predications which should be deleted...')
    subquery = session.query(PredicationToDelete.predication_id).subquery()
    stmt = delete(Predication).where(Predication.id.in_(subquery))
    session.execute(stmt)
    logging.info('Commiting...')
    session.commit()
    clean_predication_to_delete_table(session)


def clean_unreferenced_sentences():
    session = SessionExtended.get()
    logging.info('Querying all sentence ids...')
    all_sent_ids = set()
    for r in session.execute(session.query(Sentence.id)):
        all_sent_ids.add(int(r[0]))
    logging.info(f'{len(all_sent_ids)} sentence ids are in sentence table')
    logging.info('Querying referenced sentence ids...')
    ref_sent_ids = set()
    for r in session.execute(session.query(Predication.sentence_id)):
        ref_sent_ids.add(int(r[0]))
    logging.info(f'{len(ref_sent_ids)} sentence ids are used in predication table')
    sent_ids_to_delete = all_sent_ids - ref_sent_ids
    logging.info(f'{len(sent_ids_to_delete)} sentences will be deleted')

    insert_predication_ids_to_delete(sent_ids_to_delete)
    logging.info(f'{len(sent_ids_to_delete)} ids have been inserted')

    logging.info('Deleting all sentences which should be deleted...')
    subquery = session.query(PredicationToDelete.predication_id).subquery()
    stmt = delete(Sentence).where(Sentence.id.in_(subquery))
    session.execute(stmt)
    logging.info('Committing...')
    session.commit()
    clean_predication_to_delete_table(session)


def dosage_form_rule():
    """
    Any relation between a Chemical/Disease and a DosageForm will be updated to DOSAGE_FORM_PREDICATE
    :return: None
    """
    logging.info('Applying DosageForm rule...')
    session = SessionExtended.get()

    logging.info(
        'Updating predicate to "{}" for (DosageForm, *) pairs'.format(DOSAGE_FORM_PREDICATE))
    stmt_1 = update(Predication).where(or_(Predication.subject_type == DOSAGE_FORM,
                                           Predication.object_type == DOSAGE_FORM)). \
        values(relation=DOSAGE_FORM_PREDICATE)
    session.execute(stmt_1)
    session.commit()


def method_rule():
    """
    Any relation between a Chemical/Disease and a DosageForm will be updated to DOSAGE_FORM_PREDICATE
    :return: None
    """
    logging.info('Applying DosageForm rule...')
    session = SessionExtended.get()

    logging.info('Updating predicate to "{}" for (Method, *) pairs'.format(METHOD_PREDICATE))
    stmt_1 = update(Predication).where(or_(Predication.subject_type.in_([METHOD, LAB_METHOD]),
                                           Predication.object_type.in_([METHOD, LAB_METHOD]))). \
        values(relation=METHOD_PREDICATE)
    session.execute(stmt_1)
    session.commit()


def check_type_constraints():
    """
    Checks the type constraints
    If subject and object could be swapped to meet the constraint - they will be swapped
    Otherwise the extraction will be mapped to associate
    :return: None
    """

    preds_to_associate = set()
    preds_to_reorder = set()
    session = SessionExtended.get()

    logging.info('Counting the number of predications...')
    pred_count = session.query(Predication).count()
    logging.info(f'{pred_count} predications were found')
    logging.info('Querying predications...')
    pred_query = session.query(Predication).filter(Predication.relation != None) \
        .yield_per(BULK_QUERY_CURSOR_COUNT)
    start_time = datetime.now()
    for idx, pred in enumerate(pred_query):
        print_progress_with_eta("checking type constraints", idx, pred_count, start_time)
        if pred.relation in PREDICATE_TYPING:
            s_types, o_types = PREDICATE_TYPING[pred.relation]
            if pred.subject_type in s_types and pred.object_type in o_types:
                # if ids are wrongly ordered
                if pred.relation in SYMMETRIC_PREDICATES \
                        and are_subject_and_object_correctly_ordered(pred.subject_id, pred.object_id):
                    preds_to_reorder.add(pred.id)
                # everything is fine
                pass
            elif pred.subject_type in o_types and pred.object_type in s_types:
                # pred must be reordered
                preds_to_reorder.add(pred.id)
            else:
                # predication does not meet query constraints - map it to associate
                preds_to_associate.add(pred.id)

    logging.info(f'Mapping {len(preds_to_associate)} predications to associate...')
    insert_predication_ids_to_delete(preds_to_associate)
    subquery = session.query(PredicationToDelete.predication_id).subquery()
    stmt = update(Predication).where(Predication.id.in_(subquery)).values(relation=ASSOCIATED_PREDICATE_UNSURE)
    session.execute(stmt)
    logging.debug('Committing...')
    session.commit()
    clean_predication_to_delete_table(session)

    logging.info(f'Reordering {len(preds_to_reorder)} predication subject and objects...')
    insert_predication_ids_to_delete(preds_to_reorder)
    subquery = session.query(PredicationToDelete.predication_id).subquery()
    pred_query = session.query(Predication).filter(Predication.id.in_(subquery)) \
        .yield_per(BULK_QUERY_CURSOR_COUNT)
    predication_values = []
    start_time = datetime.now()
    for idx, pred in enumerate(pred_query):
        print_progress_with_eta("reorder subject and objects...", idx, pred_count, start_time)
        predication_values.append(dict(
            document_id=pred.document_id,
            document_collection=pred.document_collection,
            object_id=pred.subject_id,
            object_str=pred.subject_str,
            object_type=pred.subject_type,
            predicate=pred.predicate,
            relation=pred.relation,
            subject_id=pred.object_id,
            subject_str=pred.object_str,
            subject_type=pred.object_type,
            confidence=pred.confidence,
            sentence_id=pred.sentence_id,
            extraction_type=pred.extraction_type
        ))

    logging.info(f'Insert {len(predication_values)} reordered predications to database')
    Predication.bulk_insert_values_into_table(session, predication_values)
    logging.info(f'Deleting {len(preds_to_reorder)} old and wrongly ordered predications')
    subquery = session.query(PredicationToDelete.predication_id).subquery()
    stmt = delete(Predication).where(Predication.id.in_(subquery))
    session.execute(stmt)
    logging.debug('Committing...')
    session.commit()
    clean_predication_to_delete_table(session)


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logging.info('Applying rules...')
    dosage_form_rule()
    method_rule()
    check_type_constraints()
    #  clean_redundant_symmetric_predicates()
    #   clean_unreferenced_sentences()
    logging.info('Finished...')


if __name__ == "__main__":
    main()
