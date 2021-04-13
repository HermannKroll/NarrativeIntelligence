import logging
from io import StringIO
from collections import defaultdict
from datetime import datetime

from sqlalchemy import update, and_, or_, delete

from narraint.backend.database import Session
from narraint.backend.models import Predication, PredicationToDelete, Sentence
from narraint.entity.enttypes import DOSAGE_FORM, CHEMICAL, GENE, DISEASE, SPECIES, EXCIPIENT, DRUG, DRUGBANK_CHEMICAL, \
    PLANT_FAMILY, LAB_METHOD, METHOD
from narraint.cleaning.predicate_vocabulary import PRED_TO_REMOVE, DOSAGE_FORM_PREDICATE, METHOD_PREDICATE, \
    ASSOCIATED_PREDICATE_UNSURE
from narraint.progress import print_progress_with_eta
from narraint.queryengine.query_hints import sort_symmetric_arguments, SYMMETRIC_PREDICATES


BULK_INSERT_PRED_TO_DELETE_AFTER_K = 1000000


def clean_predication_to_delete_table(session):
    logging.info('Cleaning Predication To Delete Table...')
    stmt = delete(PredicationToDelete)
    session.execute(stmt)
    logging.info('Commiting...')
    session.commit()


def insert_predication_ids_to_delete(predication_ids: []):
    session = Session.get()
    start_time = datetime.now()
    if Session.is_postgres:
        logging.info('Using fast postgres copy mode...')
        f_pred_to_delete = StringIO()
        preds2delete_list = sorted(predication_ids)
        for idx, pred_id in enumerate(preds2delete_list):
            print_progress_with_eta("writing to temp file...", idx, len(predication_ids), start_time)
            if idx == 0:
                f_pred_to_delete.write(str(pred_id))
            else:
                f_pred_to_delete.write(f'\n{pred_id}')

        pred_to_delete_keys = ["predication_id"]
        logging.info('Executing copy from temp file to predication_to_delete ...')
        connection = session.connection().connection
        cursor = connection.cursor()
        f_pred_to_delete.seek(0)
        cursor.copy_from(f_pred_to_delete, 'predication_to_delete', sep='\t', columns=pred_to_delete_keys)
        logging.info('Committing...')
        connection.commit()
    else:
        logging.info('Using slower bulk insert...')
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

    logging.info(f'{len(predication_ids)} ids have been inserted')


def clean_redundant_predicate_tuples(session, symmetric_predicate_canonicalized: str):
    logging.info('Counting predication...')
    predication_count = Predication.query_predication_count(session, symmetric_predicate_canonicalized)
    logging.info('Querying relevant predication entries...')
    query = session.query(Predication.id, Predication.sentence_id,
                          Predication.subject_id, Predication.subject_type,
                          Predication.predicate,
                          Predication.object_id,  Predication.object_type)\
        .filter(Predication.predicate_canonicalized == symmetric_predicate_canonicalized)

    sentence2pred = defaultdict(set)
    preds2delete = set()
    start_time = datetime.now()
    logging.info('Computing duplicated values...')
    for idx, row in enumerate(session.execute(query)):
        p_id, sent_id, subj_id, subj_type, predicate, obj_id, obj_type = int(row[0]), int(row[1]), row[2], row[3], row[4], row[5], row[6]

        # symmetric relation - delete one direction
        sorted_arguments = sort_symmetric_arguments(subj_id, subj_type, obj_id, obj_type)
        if sorted_arguments[0] == subj_id: # are the arguments sorted correctly?
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

        print_progress_with_eta(f"computing duplicated {symmetric_predicate_canonicalized} values...",
                                idx, predication_count, start_time)

    if predication_count > 0:
        percentage = len(preds2delete) / predication_count
    else:
        percentage = 0
    logging.info(f'Delete {len(preds2delete)} of {predication_count} ({percentage})')
    insert_predication_ids_to_delete(preds2delete)


def clean_redundant_symmetric_predicates():
    session = Session.get()
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
    session = Session.get()
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
    logging.info('Commiting...')
    session.commit()
    clean_predication_to_delete_table(session)


def dosage_form_rule():
    """
    Any predicate_canonicalized between a Chemical/Disease and a DosageForm will be updated to DOSAGE_FORM_PREDICATE
    :return: None
    """
    logging.info('Applying DosageForm rule...')
    session = Session.get()

    logging.info(
        'Updating predicate to "{}" for (DosageForm, *) pairs'.format(DOSAGE_FORM_PREDICATE))
    stmt_1 = update(Predication).where(Predication.subject_type == DOSAGE_FORM). \
        values(predicate_canonicalized=DOSAGE_FORM_PREDICATE)
    session.execute(stmt_1)
    session.commit()

    logging.info('Deleting all dosage forms that are not in subject position...')
    stmt = delete(Predication).where(Predication.object_type == DOSAGE_FORM)
    session.execute(stmt)
    session.commit()


def method_rule():
    """
    Any predicate_canonicalized between a Chemical/Disease and a DosageForm will be updated to DOSAGE_FORM_PREDICATE
    :return: None
    """
    logging.info('Applying DosageForm rule...')
    session = Session.get()

    logging.info('Updating predicate to "{}" for (Method, *) pairs'.format(METHOD_PREDICATE))
    stmt_1 = update(Predication).where(Predication.subject_type.in_([METHOD, LAB_METHOD])). \
        values(predicate_canonicalized=METHOD_PREDICATE)
    session.execute(stmt_1)
    session.commit()

    logging.info('Deleting all methods and lab methods that are not in subject position...')
    stmt = delete(Predication).where(Predication.object_type.in_([METHOD, LAB_METHOD]))
    session.execute(stmt)
    session.commit()


def clean_extractions_in_database():
    """
    Some predicates are typed, e.g. treatments are between Chemical and Diseases - all other combinations are removed
    :return:
    """
    session = Session.get()

    logging.info('Cleaning administered (DosageForm -> *)...')
    q_administered = update(Predication).where(and_(Predication.predicate_canonicalized == 'administered',
                                                    Predication.subject_type != DOSAGE_FORM)) \
        .values(predicate_canonicalized=ASSOCIATED_PREDICATE_UNSURE)
    session.execute(q_administered)

    logging.info('Cleaning method (Method, *)...')
    q_methods = update(Predication).where(and_(Predication.predicate_canonicalized == METHOD_PREDICATE,
                                               Predication.subject_type.notin_([METHOD, LAB_METHOD]))). \
        values(predicate_canonicalized=ASSOCIATED_PREDICATE_UNSURE)
    session.execute(q_methods)

    logging.info('Cleaning induces ([Chemical, Disease] -> [Chemical, Disease])')
    q_induces = update(Predication).where(and_(Predication.predicate_canonicalized == 'induces',
                                               or_(Predication.subject_type.notin_([CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE, PLANT_FAMILY]),
                                                   Predication.object_type.notin_([CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE, PLANT_FAMILY])))) \
        .values(predicate_canonicalized=ASSOCIATED_PREDICATE_UNSURE)
    session.execute(q_induces)

    logging.info('Cleaning decreases ([Chemical, Disease] -> [Chemical, Disease])')
    q_decrease = update(Predication).where(and_(Predication.predicate_canonicalized == 'decreases',
                                                or_(Predication.subject_type.notin_([CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE, PLANT_FAMILY]),
                                                    Predication.object_type.notin_([CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, DISEASE, PLANT_FAMILY])))) \
        .values(predicate_canonicalized=ASSOCIATED_PREDICATE_UNSURE)
    session.execute(q_decrease)

    logging.info('Cleaning interacts ([Chemical, Gene] -> [Chemical, Gene])')
    q_interacts = update(Predication).where(and_(Predication.predicate_canonicalized == 'interacts',
                                                 or_(Predication.subject_type.notin_([CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, GENE, PLANT_FAMILY]),
                                                     Predication.object_type.notin_([CHEMICAL, DRUG, EXCIPIENT, DRUGBANK_CHEMICAL, GENE, PLANT_FAMILY])))) \
        .values(predicate_canonicalized=ASSOCIATED_PREDICATE_UNSURE)
    session.execute(q_interacts)

    logging.info('Cleaning metabolises (Gene -> Chemical)')
    q_metabolises = update(Predication).where(and_(Predication.predicate_canonicalized == 'metabolises',
                                                   or_(Predication.subject_type != GENE,
                                                       Predication.object_type.notin_([CHEMICAL, DRUG, DRUGBANK_CHEMICAL, EXCIPIENT, PLANT_FAMILY])))) \
        .values(predicate_canonicalized=ASSOCIATED_PREDICATE_UNSURE)
    session.execute(q_metabolises)

    logging.info('Cleaning inhibits (Chemical -> Gene)')
    q_inhibits = update(Predication).where(and_(Predication.predicate_canonicalized == 'inhibits',
                                                or_(Predication.subject_type.notin_([CHEMICAL, DRUG, DRUGBANK_CHEMICAL, EXCIPIENT, PLANT_FAMILY]),
                                                    Predication.object_type != GENE))) \
        .values(predicate_canonicalized=ASSOCIATED_PREDICATE_UNSURE)
    session.execute(q_inhibits)

    # Delete all treatments which are not (Chemical -> Disease, Species)
    logging.info('Cleaning treats (Chemical -> [Disease, Species])...')
    q_treatment = update(Predication).where(and_(Predication.predicate_canonicalized == 'treats',
                                                 or_(Predication.subject_type.notin_([CHEMICAL, DRUG, PLANT_FAMILY, DRUGBANK_CHEMICAL, EXCIPIENT]),
                                                     Predication.object_type.notin_([DISEASE, SPECIES])))) \
        .values(predicate_canonicalized=ASSOCIATED_PREDICATE_UNSURE)
    session.execute(q_treatment)

    logging.info(f'Update all {PRED_TO_REMOVE} predicates to {ASSOCIATED_PREDICATE_UNSURE}...')
    q_update = update(Predication).where(Predication.predicate_canonicalized == PRED_TO_REMOVE)\
        .values(predicate_canonicalized=ASSOCIATED_PREDICATE_UNSURE)
    session.execute(q_update)

    logging.info(f'Update all null predicates to {ASSOCIATED_PREDICATE_UNSURE}...')
    q_update = update(Predication).where(Predication.predicate_canonicalized.is_(None))\
        .values(predicate_canonicalized=ASSOCIATED_PREDICATE_UNSURE)
    session.execute(q_update)

    logging.info('Committing updates...')
    session.commit()


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logging.info('Applying rules...')
    dosage_form_rule()
    method_rule()
    clean_extractions_in_database()
    clean_redundant_symmetric_predicates()
    clean_unreferenced_sentences()
    logging.info('Finished...')


if __name__ == "__main__":
    main()
