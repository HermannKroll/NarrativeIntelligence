import logging
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import update, and_, or_
from sqlalchemy.exc import IntegrityError

from narraint.entity.entityresolver import GeneResolver
from narraint.backend.database import Session
from narraint.backend.models import Predication, PredicationResult
from narraint.entity.enttypes import DOSAGE_FORM, CHEMICAL, GENE, SPECIES, DISEASE
from narraint.entity.genemapper import GeneMapper
from narraint.progress import print_progress_with_eta

DOSAGE_FORM_PREDICATE = "dosageform"
ASSOCIATED_PREDICATE = "associated"
SYMMETRIC_PREDICATES = {DOSAGE_FORM_PREDICATE, ASSOCIATED_PREDICATE}


def dosage_form_rule():
    """
    Any predicate_canonicalized between a Chemical/Disease and a DosageForm will be updated to DOSAGE_FORM_PREDICATE
    :return: None
    """
    logging.info('Applying DosageForm rule...')
    session = Session.get()

    logging.info('Updating predicate to "{}" for (DosageForm, Chemical) pairs'.format(DOSAGE_FORM))
    stmt_1 = update(Predication).where(and_(Predication.subject_type == DOSAGE_FORM,
                                            Predication.object_type == CHEMICAL)). \
        values(predicate_canonicalized=DOSAGE_FORM_PREDICATE)
    session.execute(stmt_1)
    session.commit()

    logging.info('Updating predicate to "{}" for (Chemical, DosageForm) pairs'.format(DOSAGE_FORM))
    stmt_2 = update(Predication).where(and_(Predication.subject_type == CHEMICAL,
                                            Predication.object_type == DOSAGE_FORM)). \
        values(predicate_canonicalized=DOSAGE_FORM_PREDICATE)
    session.execute(stmt_2)
    session.commit()

    logging.info('Updating predicate to "{}" for (DosageForm, Disease) pairs'.format(DOSAGE_FORM))
    stmt_1 = update(Predication).where(and_(Predication.subject_type == DOSAGE_FORM,
                                            Predication.object_type == DISEASE)). \
        values(predicate_canonicalized=DOSAGE_FORM_PREDICATE)
    session.execute(stmt_1)
    session.commit()

    logging.info('Updating predicate to "{}" for (Disease, DosageForm) pairs'.format(DOSAGE_FORM))
    stmt_2 = update(Predication).where(and_(Predication.subject_type == DISEASE,
                                            Predication.object_type == DOSAGE_FORM)). \
        values(predicate_canonicalized=DOSAGE_FORM_PREDICATE)
    session.execute(stmt_2)
    session.commit()


def mirror_symmetric_predicates():
    """
    Some predicates are symmetric - these predicates will be mirrored in the database
    :return: None
    """
    session = Session.get()
    logging.info('Deleting old mirrored predicates...')
    session.query(Predication).filter(Predication.mirrored == True).delete()
    session.commit()
    logging.info('Deleted')
    logging.info('Mirroring symmetric predicates...')
    for idx_pred, pred_to_mirror in enumerate(SYMMETRIC_PREDICATES):
        start_time = datetime.now()
        logging.info('Mirroring predicate: {}'.format(pred_to_mirror))
        q = session.query(Predication)
        q = q.filter(Predication.mirrored == False).filter(Predication.predicate_canonicalized == pred_to_mirror)
        count_mirrored = 0
        for r in session.execute(q):
            p = PredicationResult(*r)

            try:
                insert_pred = insert(Predication).values(
                    document_id=p.document_id,
                    document_collection=p.document_collection,
                    subject_openie=p.object_openie,
                    subject_id=p.object_id,
                    subject_str=p.object_str,
                    subject_type=p.object_type,
                    predicate=p.predicate,
                    predicate_cleaned=p.predicate_cleaned,
                    predicate_canonicalized=p.predicate_canonicalized,
                    object_openie=p.subject_openie,
                    object_id=p.subject_id,
                    object_str=p.subject_str,
                    object_type=p.subject_type,
                    confidence=p.confidence,
                    sentence=p.sentence,
                    mirrored=True,
                    extraction_type=p.extraction_type,
                    extraction_version=p.extraction_version
                )
                session.execute(insert_pred)
                session.commit()
            except IntegrityError:
                logging.warning('Skip duplicated fact: ({}, {}, {}, {}, {}, {})'.
                                format(p.document_id, p.document_collection, p.subject_id, p.predicate, p.object_id,
                                       p.sentence))

                session.rollback()
                session.commit()
            count_mirrored += 1
        logging.info('{} facts mirrored for predicate: {} (in {}s)'.format(count_mirrored, pred_to_mirror,
                                                                           datetime.now() - start_time))

    logging.info('Mirroring predicates finished')


def clean_extractions_in_database():
    """
    Some predicates are typed, e.g. treatments are between Chemical and Diseases - all other combinations are removed
    :return:
    """
    session = Session.get()

    # Delete all treatments which are not (Chemical -> Disease)
    logging.info('Cleaning treats (Chemical -> Disease)...')
    q_treatment = update(Predication).where(and_(Predication.predicate_canonicalized == 'treats',
                                                 or_(Predication.subject_type != CHEMICAL,
                                                     Predication.object_type != DISEASE))) \
        .values(predicate_canonicalized=None)
    session.execute(q_treatment)
    session.commit()

    logging.info('Cleaning decreases (Chemical -> ...)')
    q_decrease = update(Predication).where(and_(Predication.predicate_canonicalized == 'decreases',
                                                Predication.subject_type != CHEMICAL)) \
        .values(predicate_canonicalized=None)
    session.execute(q_decrease)
    session.commit()

    logging.info('Cleaning induces (Chemical -> Chemical / Disease)')
    q_cause = update(Predication).where(and_(Predication.predicate_canonicalized == 'induces',
                                             or_(Predication.object_type != DISEASE,
                                                 and_(Predication.subject_type != CHEMICAL,
                                                      Predication.subject_type != DISEASE)))) \
        .values(predicate_canonicalized=None)
    session.execute(q_cause)
    session.commit()

    logging.info('Cleaning inhibits (Chemical -> Gene)')
    q_inhibits = update(Predication).where(and_(Predication.predicate_canonicalized == 'inhibits',
                                                or_(Predication.subject_type != CHEMICAL,
                                                    Predication.object_type != GENE))) \
        .values(predicate_canonicalized=None)
    session.execute(q_inhibits)
    session.commit()


def split_predications_with_multiple_gene_ids():
    """
    Some extractions may contain several gene ids (these gene ids are encoded as "id1;id2;id3" as tags)
    This method splits these extraction in single facts with only a single gene id for each
    :return: None
    """
    logging.info('Splitting multiple gene ids...')
    session = Session.get()
    logging.info('Querying Predications with multiple genes..')
    q = session.query(Predication).filter(
        or_(and_(Predication.subject_type == GENE, Predication.subject_id.like('%;%')),
            and_(Predication.object_type == GENE, Predication.object_id.like('%;%'))))

    start_time = datetime.now()
    result_size = session.query(Predication).filter(
        or_(and_(Predication.subject_type == GENE, Predication.subject_id.like('%;%')),
            and_(Predication.object_type == GENE, Predication.object_id.like('%;%')))).count()
    logging.info('{} extractions have several gene ids...'.format(result_size))
    for idx, row in enumerate(session.execute(q)):
        print_progress_with_eta("splitting gene ids...", idx, result_size, start_time, print_every_k=100)
        p = PredicationResult(*row)
        if p.subject_type == GENE and ';' in p.subject_id:
            subject_gene_ids = p.subject_id.split(';')
        else:
            subject_gene_ids = [p.subject_id]
        if p.object_type == GENE and ';' in p.object_id:
            object_gene_ids = p.object_id.split(';')
        else:
            object_gene_ids = [p.object_id]

        # insert cross product of gene combinations
        for subj_gene_id in subject_gene_ids:
            for obj_gene_id in object_gene_ids:
                try:
                    insert_pred = insert(Predication).values(
                        document_id=p.document_id,
                        document_collection=p.document_collection,
                        subject_openie=p.subject_openie,
                        subject_id=subj_gene_id,
                        subject_str=p.subject_str,
                        subject_type=p.subject_type,
                        predicate=p.predicate,
                        predicate_cleaned=p.predicate_cleaned,
                        predicate_canonicalized=p.predicate_canonicalized,
                        object_openie=p.object_openie,
                        object_id=obj_gene_id,
                        object_str=p.object_str,
                        object_type=p.object_type,
                        confidence=p.confidence,
                        sentence=p.sentence,
                        mirrored=False,
                        extraction_type=p.extraction_type,
                        extraction_version=p.extraction_version
                    )
                    session.execute(insert_pred)
                    session.commit()
                except IntegrityError:
                    logging.warning('Skip duplicated fact: ({}, {}, {}, {}, {}, {})'.
                                    format(p.document_id, p.document_collection, subj_gene_id, p.predicate, obj_gene_id,
                                           p.sentence))

                    session.rollback()
                    session.commit()


def remove_predications_with_multiple_genes():
    """
    Removes all Predications with multiple gene ids
    :return: None
    """
    session = Session.get()
    logging.info('Querying Predications with multiple genes..')
    result_size = session.query(Predication).filter(
        or_(and_(Predication.subject_type == GENE, Predication.subject_id.like('%;%')),
            and_(Predication.object_type == GENE, Predication.object_id.like('%;%')))).count()

    if result_size > 0:
        logging.info('Deleting {} Predications with multiple genes..'.format(result_size))
        q = session.query(Predication).filter(
            or_(and_(Predication.subject_type == GENE, Predication.subject_id.like('%;%')),
                and_(Predication.object_type == GENE, Predication.object_id.like('%;%')))).delete(synchronize_session=False)
        # synchronize_session must be false because the operation directly works in the database
        session.commit()
    logging.info('{} predications were deleted'.format(result_size))


def remap_gene_ids_to_symbols():
    """
    Gene IDs are unique for each species - We are only interested in the names of genes
    Thus, we map each gene id to its gene symbol, so that, e.g. CYP3A4 is the unique description for all species
    :return:
    """
    logging.info('Loading GeneResolver...')
    gene_resolver = GeneResolver()
    gene_resolver.load_index()

    logging.info('Remapping gene ids...')
    session = Session.get()
    db_gene_ids = set()
    logging.info('Querying subject gene ids...')
    q_s = session.query(Predication.subject_id).filter(Predication.subject_type == GENE)
    for r in session.execute(q_s):
        db_gene_ids.add(r[0])
    logging.info('Querying object gene ids...')
    q_o = session.query(Predication.object_id).filter(Predication.object_type == GENE)
    for r in session.execute(q_o):
        db_gene_ids.add(r[0])

    logging.info('Processing gene ids...')
    gene_ids_len = len(db_gene_ids)
    start_time = datetime.now()
    for idx, gene_id in enumerate(db_gene_ids):
        try:
            symbol = gene_resolver.gene_id_to_symbol(gene_id).lower()
            q_update_gene_subject = update(Predication).where(and_(Predication.subject_type == GENE,
                                                                   Predication.subject_id == gene_id)) \
                .values(subject_id=symbol)
            session.execute(q_update_gene_subject)
            q_update_gene_object = update(Predication).where(and_(Predication.object_type == GENE,
                                                                  Predication.object_id == gene_id)) \
                .values(object_id=symbol)
            session.execute(q_update_gene_object)
            session.commit()

            #print('map {} to {}'.format(gene_id, symbol))
        except ValueError:
            print('skipping gene id: {}'.format(gene_id))
            continue
        except KeyError:
            print('GeneResolver cannot map {}'.format(gene_id))
            continue
        print_progress_with_eta("updating genes", idx, gene_ids_len, start_time, print_every_k=10)


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    dosage_form_rule()
    mirror_symmetric_predicates()
    clean_extractions_in_database()

    # Gene Stuff
    # split_predications_with_multiple_gene_ids()
    # remove_predications_with_multiple_genes()
    # remap_gene_ids_to_symbols()


if __name__ == "__main__":
    main()
