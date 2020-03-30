import argparse
import logging
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import update, and_

from narraint.backend.database import Session
from narraint.backend.models import Predication, PredicationResult
from narraint.entity.enttypes import DOSAGE_FORM, CHEMICAL, GENE, SPECIES

DOSAGE_FORM_PREDICATE = "dosageform"
COMMIT_AFTER_K = 1000
SYMMETRIC_PREDICATES = {DOSAGE_FORM_PREDICATE}


def dosage_form_rule():
    logging.info('Applying DosageForm rule...')
    session = Session.get()

    logging.info('Updating predicate to "{}" for (DosageForm, Chemical) pairs'.format(DOSAGE_FORM))
    stmt_1 = update(Predication).where(and_(Predication.subject_type == DOSAGE_FORM,
                                            Predication.object_type == CHEMICAL)).\
        values(predicate_canonicalized=DOSAGE_FORM_PREDICATE)
    session.execute(stmt_1)
    session.commit()

    logging.info('Updating predicate to "{}" for (Chemical, DosageForm) pairs'.format(DOSAGE_FORM))
    stmt_2 = update(Predication).where(and_(Predication.subject_type == CHEMICAL,
                                            Predication.object_type == DOSAGE_FORM)). \
        values(predicate_canonicalized=DOSAGE_FORM_PREDICATE)
    session.execute(stmt_2)
    session.commit()


def mirror_symmetric_predicates():
    logging.info('Mirroring symmetric predicates...')
    session = Session.get()

    for idx_pred, pred_to_mirror in enumerate(SYMMETRIC_PREDICATES):
        start_time = datetime.now()
        logging.info('Mirroring predicate: {}'.format(pred_to_mirror))
        q = session.query(Predication)
        q = q.filter(Predication.mirrored == False).filter(Predication.predicate_canonicalized == pred_to_mirror)
        count_mirrored = 0
        for r in session.execute(q):
            p = PredicationResult(*r)
            insert_pred = insert(Predication).values(
                document_id=p.document_id,
                document_collection=p.document_collection,
                subject_openie=p.subject_openie,
                subject_id=p.object_id,
                subject_str=p.object_str,
                subject_type=p.object_type,
                predicate=p.predicate,
                predicate_cleaned=p.predicate_cleaned,
                predicate_canonicalized=p.predicate_canonicalized,
                object_openie=p.object_openie,
                object_id=p.subject_id,
                object_str=p.subject_str,
                object_type=p.subject_type,
                confidence=p.confidence,
                sentence=p.sentence,
                mirrored=True,
                openie_version=p.openie_version
            ).on_conflict_do_nothing(
                index_elements=('document_id', 'document_collection', 'subject_id', 'predicate', 'object_id', 'sentence')
            )
            count_mirrored += 1
            session.execute(insert_pred)
            if count_mirrored % COMMIT_AFTER_K:
                session.commit()
        session.commit()
        logging.info('{} facts mirrored for predicate: {} (in {}s)'.format(count_mirrored, pred_to_mirror,
                                                                           datetime.now()-start_time))

    logging.info('Mirroring predicates finished')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    dosage_form_rule()
    mirror_symmetric_predicates()


if __name__ == "__main__":
    main()
