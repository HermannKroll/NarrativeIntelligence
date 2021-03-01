import os

import logging
from collections import defaultdict

from sqlalchemy import insert

from narraint.backend.database import Session
from narraint.backend.export import export
from narraint.backend.models import Document, Tag, Predication
from narraint.config import DATA_DIR
from narraint.entity import enttypes
from narraint.entity.enttypes import DISEASE, CHEMICAL, GENE
from narraint.extraction.apply_rules import clean_extractions_in_database
from narraint.extraction.canonicalize_predicates import canonicalize_predication_table
from narraint.extraction.openie.cleanload import insert_predications_into_db, read_stanford_openie_input, clean_open_ie
from narraint.extraction.openie.main import run_corenlp_openie
from narraint.extraction.openie6.main import run_openie6
from narraint.extraction.pathie.load_extractions import read_pathie_extractions_tsv
from narraint.extraction.pathie.main import run_pathie
from narraint.extraction.pathie_stanza.main import run_stanza_pathie
from narraint.extraction.versions import PATHIE_EXTRACTION, PATHIE_STANZA_EXTRACTION, OPENIE6_EXTRACTION, \
    OPENIE_EXTRACTION

CHEMPROT_DIR = os.path.join(DATA_DIR, 'extraction/chemprot_test')
CHEMPROT_COLLECTION = 'ChemProt'

CHEMPROT_DOCUMENTS = os.path.join(CHEMPROT_DIR, 'chemprot_test_abstracts_gs.tsv')
CHEMPROT_TAGS_TSV = os.path.join(CHEMPROT_DIR, 'chemprot_test_entities_gs.tsv')
CHEMPROT_RELATIONS_TSV = os.path.join(CHEMPROT_DIR, 'chemprot_test_relations_gs.tsv')

CHEMPROT_OUTPUT_DIR = os.path.join(CHEMPROT_DIR, 'output')

CHEMPROT_PUBTATOR = os.path.join(CHEMPROT_OUTPUT_DIR, 'documents.pubtator')
CHEMPROT_PATHIE_OUTPUT = os.path.join(CHEMPROT_OUTPUT_DIR, "pathie_V2.tsv")
CHEMPROT_PATHIE_STANZA_OUTPUT = os.path.join(CHEMPROT_OUTPUT_DIR, 'pathie_stanza_V2.tsv')

CHEMPROT_OPENIE_OUTPUT = os.path.join(CHEMPROT_OUTPUT_DIR, 'openie.tsv')
CHEMPROT_OPENIE6_OUTPUT = os.path.join(CHEMPROT_OUTPUT_DIR, 'openie6.tsv')

CP_canonicalizing_distances = os.path.join(CHEMPROT_OUTPUT_DIR, 'canonicalizing_distances.tsv')
WORD2VEC_MODEL = '/home/kroll/workingdir/BioWordVec_PubMed_MIMICIII_d200.bin'


CP_LOAD_DOCUMENTS_AND_TAGS = False
CP_EXPORT_PUBTATOR_DOCUMENTS = False

RUN_PATHIE = False
LOAD_PATHIE = False

RUN_STANZA_PATHIE = False
LOAD_STANZA_PATHIE = False


RUN_CORENLP_OPENIE = False
LOAD_CORENLP_OPENIE = False

RUN_OPENIE6 = False
LOAD_OPENIE6 = False


CANONICALIZE_OUTPUT = False


def perform_chemprot_evaluation(correct_relations, extraction_type):
    relations = ['inhibits']#['inhibits', 'induces']
    session = Session.get()
    q = session.query(Predication.document_id, Predication.predicate_canonicalized,
                      Predication.subject_id, Predication.object_id) \
        .filter(Predication.document_collection == CHEMPROT_COLLECTION) \
        .filter(Predication.predicate_canonicalized.in_(relations))\
        .filter(Predication.subject_type == CHEMICAL)\
        .filter(Predication.object_type == GENE)\
        .filter(Predication.extraction_type == extraction_type)

    extracted_relations = defaultdict(set)
    for r in session.execute(q):
        doc_id, relation, subject_id, object_id = int(r[0]), r[1], r[2], r[3]
        extracted_relations[doc_id].add((relation, subject_id, object_id))

    count_correct_extractions = 0
    count_wrong_extractions = 0
    for doc_id, extractions in extracted_relations.items():
        if doc_id in correct_relations:
            for p, s, o in extractions:
                if (p, s, o) in correct_relations[doc_id] or (p, o, s) in correct_relations[doc_id]:
                    count_correct_extractions += 1
                else:
                    count_wrong_extractions += 1
        else:
            count_wrong_extractions += len(extractions)

    count_missing_extractions = 0
    for doc_id, extractions in correct_relations.items():
        if doc_id in extracted_relations:
            for p, s, o in extractions:
                if (p, s, o) not in extracted_relations[doc_id] and (p, o, s) not in extracted_relations[doc_id]:
                    count_missing_extractions += 1
        else:
            count_missing_extractions += len(extractions)

    precision = count_correct_extractions / (count_correct_extractions + count_wrong_extractions)
    recall = count_correct_extractions / (count_correct_extractions + count_missing_extractions)
    f1 = (2 * precision * recall) / (precision + recall)
    logging.info(f'Precision: {precision}')
    logging.info(f'Recall: {recall}')
    logging.info(f'F1-measure: {f1} ')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    if not os.path.isdir(CHEMPROT_OUTPUT_DIR):
        os.mkdir(CHEMPROT_OUTPUT_DIR)

    if CP_LOAD_DOCUMENTS_AND_TAGS:
        logging.info('Loading documents...')
        session = Session.get()
        with open(CHEMPROT_DOCUMENTS, 'rt') as f:
            for line in f:
                doc_id, title, abstract = line.split('\t', maxsplit=2)

                insert_document = insert(Document).values(
                    collection=CHEMPROT_COLLECTION,
                    id=int(doc_id),
                    title=title,
                    abstract=abstract,
                )
                session.execute(insert_document)
        logging.info('Loading tags...')
        with open(CHEMPROT_TAGS_TSV, 'rt') as f:
            for line in f:
                doc_id, ent_id, ent_type, start, end, ent_str = line.replace('\n', '').split('\t')
                if ent_type == 'CHEMICAL':
                    ent_type = CHEMICAL
                else:
                    ent_type = GENE

                insert_tag = insert(Tag).values(
                    ent_type=ent_type,
                    start=start,
                    end=end,
                    ent_id=ent_id,
                    ent_str=ent_str,
                    document_id=int(doc_id),
                    document_collection=CHEMPROT_COLLECTION,
                )
                session.execute(insert_tag)
        logging.info('Commit loading...')
        session.commit()

    if CP_EXPORT_PUBTATOR_DOCUMENTS:
        logging.info(f'Exporting ChemProt PubTator documents... ({CHEMPROT_PUBTATOR})')
        export(CHEMPROT_PUBTATOR, [CHEMICAL, GENE], collection=CHEMPROT_COLLECTION)

    if RUN_PATHIE:
        logging.info('Running PathIE...')
        run_pathie(CHEMPROT_PUBTATOR, CHEMPROT_PATHIE_OUTPUT)

    if LOAD_PATHIE:
        logging.info('Reading extraction from tsv file...')
        predications = read_pathie_extractions_tsv(CHEMPROT_PATHIE_OUTPUT)
        logging.info('{} extractions read'.format(len(predications)))
        insert_predications_into_db(predications, CHEMPROT_COLLECTION, extraction_type=PATHIE_EXTRACTION,
                                    clean_genes=False)
        logging.info('finished')

    if RUN_STANZA_PATHIE:
        logging.info('Running Stanza PathIE...')
        run_stanza_pathie(CHEMPROT_PUBTATOR, CHEMPROT_PATHIE_STANZA_OUTPUT)

    if LOAD_STANZA_PATHIE:
        logging.info('Reading extraction from tsv file...')
        predications = read_pathie_extractions_tsv(CHEMPROT_PATHIE_STANZA_OUTPUT)
        logging.info('{} extractions read'.format(len(predications)))
        insert_predications_into_db(predications, CHEMPROT_COLLECTION, extraction_type=PATHIE_STANZA_EXTRACTION,
                                    clean_genes=False)
        logging.info('finished')

    if RUN_CORENLP_OPENIE:
        logging.info('Running StanfordCoreNLP...')
        run_corenlp_openie(CHEMPROT_PUBTATOR, CHEMPROT_OPENIE_OUTPUT)

    if LOAD_CORENLP_OPENIE:
        logging.info('Loading CoreNLP OpenIE extractions...')
        doc_ids, openie_tuples = read_stanford_openie_input(CHEMPROT_OPENIE_OUTPUT)
        clean_open_ie(doc_ids, openie_tuples, CHEMPROT_COLLECTION, clean_genes=False)
        logging.info('finished')

    if RUN_OPENIE6:
        logging.info('Running OpenIE6...')
        run_openie6(CHEMPROT_PUBTATOR, CHEMPROT_OPENIE6_OUTPUT)

    if LOAD_OPENIE6:
        logging.info('Loading OpenIE 6.0 extractions...')
        doc_ids, openie_tuples = read_stanford_openie_input(CHEMPROT_OPENIE6_OUTPUT)
        clean_open_ie(doc_ids, openie_tuples, CHEMPROT_COLLECTION, extraction_type=OPENIE6_EXTRACTION, clean_genes=False)
        logging.info('finished')

    if CANONICALIZE_OUTPUT:
        logging.info('Canonicalizing output...')
        canonicalize_predication_table(WORD2VEC_MODEL, CP_canonicalizing_distances)
        clean_extractions_in_database()

    logging.info('Loading correct relations...')
    gold_relations = defaultdict(set)
    with open(CHEMPROT_RELATIONS_TSV, 'rt') as f:
        for line in f:
            doc_id, relation_type, do_eval, relation, arg1, arg2 = line.replace('\n', '').split('\t')
            doc_id = int(doc_id)
            arg1 = arg1[5:]
            arg2 = arg2[5:]
            if relation_type == 'CPR:4':
                gold_relations[doc_id].add(('inhibits', arg1, arg2))
            #if relation_type == 'CPR:3':
             #   gold_relations[doc_id].add(('upregulates', arg1, arg2))

    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {PATHIE_EXTRACTION}...')
    perform_chemprot_evaluation(gold_relations, PATHIE_EXTRACTION)
    logging.info('=' * 60)

    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {PATHIE_STANZA_EXTRACTION}...')
    perform_chemprot_evaluation(gold_relations, PATHIE_STANZA_EXTRACTION)
    logging.info('=' * 60)

    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {OPENIE_EXTRACTION}...')
    perform_chemprot_evaluation(gold_relations, OPENIE_EXTRACTION)
    logging.info('=' * 60)

    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {OPENIE6_EXTRACTION}...')
    perform_chemprot_evaluation(gold_relations, OPENIE6_EXTRACTION)
    logging.info('=' * 60)


if __name__ == "__main__":
    main()
