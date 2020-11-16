import logging
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import update, and_, or_
from sqlalchemy.exc import IntegrityError

from narraint.backend.database import Session
from narraint.backend.models import Predication, PredicationResult
from narraint.entity.enttypes import DOSAGE_FORM, CHEMICAL, GENE, DISEASE, SPECIES, EXCIPIENT, DRUG
from narraint.entity.meshontology import MeSHOntology
from narraint.extraction.openie.cleanload import BULK_INSERT_AFTER_K, _insert_predication_skip_duplicates
from narraint.progress import print_progress_with_eta

DOSAGE_FORM_PREDICATE = "administered"
ASSOCIATED_PREDICATE = "associated"
SYMMETRIC_PREDICATES = {DOSAGE_FORM_PREDICATE}  # , ASSOCIATED_PREDICATE}


def dosage_form_rule():
    """
    Any predicate_canonicalized between a Chemical/Disease and a DosageForm will be updated to DOSAGE_FORM_PREDICATE
    :return: None
    """
    logging.info('Applying DosageForm rule...')
    session = Session.get()

    logging.info(
        'Updating predicate to "{}" for (DosageForm, [Chemical, Disease, Species]) pairs'.format(DOSAGE_FORM_PREDICATE))
    stmt_1 = update(Predication).where(and_(Predication.subject_type == DOSAGE_FORM,
                                            Predication.object_type.in_([CHEMICAL, DISEASE, SPECIES, DRUG, EXCIPIENT]))). \
        values(predicate_canonicalized=DOSAGE_FORM_PREDICATE)
    session.execute(stmt_1)
    session.commit()


def clean_extractions_in_database():
    """
    Some predicates are typed, e.g. treatments are between Chemical and Diseases - all other combinations are removed
    :return:
    """
    session = Session.get()

    logging.info('Cleaning administered (DosageForm -> [Chemical, Disease Species])...')
    q_administered = update(Predication).where(and_(Predication.predicate_canonicalized == 'administered',
                                                    or_(Predication.subject_type != DOSAGE_FORM,
                                                        Predication.object_type.notin_([SPECIES, DISEASE, CHEMICAL, DRUG, EXCIPIENT])))) \
        .values(predicate_canonicalized=None)
    session.execute(q_administered)
    session.commit()

    logging.info('Cleaning induces ([Chemical, Disease] -> [Chemical, Disease])')
    q_induces = update(Predication).where(and_(Predication.predicate_canonicalized == 'induces',
                                               or_(Predication.subject_type.notin_([CHEMICAL, DRUG, EXCIPIENT, DISEASE]),
                                                   Predication.object_type.notin_([CHEMICAL, DRUG, EXCIPIENT, DISEASE])))) \
        .values(predicate_canonicalized=None)
    session.execute(q_induces)
    session.commit()

    logging.info('Cleaning decreases ([Chemical, Disease] -> [Chemical, Disease])')
    q_decrease = update(Predication).where(and_(Predication.predicate_canonicalized == 'decreases',
                                                or_(Predication.subject_type.notin_([CHEMICAL, DRUG, EXCIPIENT, DISEASE]),
                                                    Predication.object_type.notin_([CHEMICAL, DRUG, EXCIPIENT, DISEASE])))) \
        .values(predicate_canonicalized=None)
    session.execute(q_decrease)
    session.commit()

    logging.info('Cleaning interacts ([Chemical, Gene] -> [Chemical, Gene])')
    q_interacts = update(Predication).where(and_(Predication.predicate_canonicalized == 'interacts',
                                                 or_(Predication.subject_type.notin_([CHEMICAL, DRUG, EXCIPIENT, GENE]),
                                                     Predication.object_type.notin_([CHEMICAL, DRUG, EXCIPIENT, GENE])))) \
        .values(predicate_canonicalized=None)
    session.execute(q_interacts)
    session.commit()

    logging.info('Cleaning metabolises (Gene -> Chemical)')
    q_metabolises = update(Predication).where(and_(Predication.predicate_canonicalized == 'metabolises',
                                                   or_(Predication.subject_type != GENE,
                                                       Predication.object_type.notin_([CHEMICAL, DRUG, EXCIPIENT])))) \
        .values(predicate_canonicalized=None)
    session.execute(q_metabolises)
    session.commit()

    logging.info('Cleaning inhibits (Chemical -> Gene)')
    q_inhibits = update(Predication).where(and_(Predication.predicate_canonicalized == 'inhibits',
                                                or_(Predication.subject_type.notin_([CHEMICAL, DRUG, EXCIPIENT]),
                                                    Predication.object_type != GENE))) \
        .values(predicate_canonicalized=None)
    session.execute(q_inhibits)
    session.commit()

    # Delete all treatments which are not (Chemical -> Disease, Species)
    logging.info('Cleaning treats (Chemical -> [Disease, Species])...')
    q_treatment = update(Predication).where(and_(Predication.predicate_canonicalized == 'treats',
                                                 or_(Predication.subject_type.notin_([CHEMICAL, DRUG, EXCIPIENT]),
                                                     Predication.object_type.notin_([DISEASE, SPECIES])))) \
        .values(predicate_canonicalized=None)
    session.execute(q_treatment)
    session.commit()


def mirror_symmetric_predicates():
    """
    Some predicates are symmetric - these predicates will be mirrored in the database
    :return: None
    """
    session = Session.get()
    logging.info('Mirroring symmetric predicates...')
    for idx_pred, pred_to_mirror in enumerate(SYMMETRIC_PREDICATES):
        start_time = datetime.now()
        logging.info('Mirroring predicate: {}'.format(pred_to_mirror))
        q = session.query(Predication)
        q = q.filter(Predication.predicate_canonicalized == pred_to_mirror)
        predication_values = []
        count_mirrored = 0
        for i, r in enumerate(session.execute(q)):
            p = PredicationResult(*r)

            try:
                predication_values.append(dict(
                    document_id=p.document_id,
                    document_collection=p.document_collection,
                    subject_id=p.object_id,
                    subject_str=p.object_str,
                    subject_type=p.object_type,
                    predicate=p.predicate,
                    predicate_canonicalized=p.predicate_canonicalized,
                    object_id=p.subject_id,
                    object_str=p.subject_str,
                    object_type=p.subject_type,
                    confidence=p.confidence,
                    sentence_id=p.sentence_id,
                    extraction_type=p.extraction_type
                ))

                if i % BULK_INSERT_AFTER_K == 0:
                    session.bulk_insert_mappings(Predication, predication_values)
                    session.commit()
                    predication_values.clear()
            except IntegrityError:
                _insert_predication_skip_duplicates(session, predication_values)
                predication_values.clear()

            count_mirrored += 1
        try:
            # commit the remaining
            session.bulk_insert_mappings(Predication, predication_values)
            session.commit()
            predication_values.clear()
        except IntegrityError:
            _insert_predication_skip_duplicates(session, predication_values)
            predication_values.clear()

        logging.info('{} facts mirrored for predicate: {} (in {}s)'.format(count_mirrored, pred_to_mirror,
                                                                           datetime.now() - start_time))

    logging.info('Mirroring predicates finished')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    dosage_form_rule()
    clean_extractions_in_database()
    # mirror_symmetric_predicates()


if __name__ == "__main__":
    main()
