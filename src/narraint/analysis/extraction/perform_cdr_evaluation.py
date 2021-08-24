import logging
import os
from collections import defaultdict

from narraint.backend.database import SessionExtended
from narrant.backend.load_document import read_tagger_mapping, UNKNOWN_TAGGER, insert_taggers, \
    document_bulk_load
from narraint.backend.models import Predication
from narraint.cleaning.relation_vocabulary import create_predicate_vocab
from narraint.config import DATA_DIR, RESOURCE_DIR
from narrant.preprocessing.enttypes import CHEMICAL, DISEASE
from narraint.cleaning.apply_rules import check_type_constraints
from narraint.cleaning.canonicalize_predicates import canonicalize_predication_table
from narraint.extraction.openie.cleanload import insert_predications_into_db, read_stanford_openie_input, clean_open_ie
from narraint.extraction.openie.main import run_corenlp_openie
from narraint.extraction.openie6.main import openie6_run
from narraint.extraction.pathie.load_extractions import read_pathie_extractions_tsv
from narraint.extraction.pathie.main import run_pathie
from narraint.extraction.pathie_stanza.main import run_stanza_pathie
from narraint.extraction.versions import PATHIE_EXTRACTION, OPENIE_EXTRACTION, PATHIE_STANZA_EXTRACTION, \
    OPENIE6_EXTRACTION
from narrant.pubtator.document import TaggedDocument
from narrant.pubtator.extract import read_pubtator_documents

pubtator_docs = ['CDR_TestSet.PubTator.txt']  # , 'CDR_DevelopmentSet.PubTator.txt', 'CDR_TrainingSet.PubTator.txt']

CDR2015_DIR = os.path.join(DATA_DIR, 'extraction/CDR2015')
CDR2015_DIR_OUTPUT = os.path.join(CDR2015_DIR, 'output')
pubtator_doc_paths = [os.path.join(CDR2015_DIR, d) for d in pubtator_docs]

CDR2015_pubtator_extracted = os.path.join(CDR2015_DIR_OUTPUT, 'cdr_documents.pubtator')
CDR2015_corenlp_openie_output = os.path.join(CDR2015_DIR_OUTPUT, 'corenlp_openie.tsv')
CDR2015_pathie_output = os.path.join(CDR2015_DIR_OUTPUT, 'pathie_extractions_V2.tsv')
CDR2015_stanza_pathie_output = os.path.join(CDR2015_DIR_OUTPUT, 'pathie_stanza_extractions_V2.tsv')
CDR2015_openie6_output = os.path.join(CDR2015_DIR_OUTPUT, 'openie6_extractions.tsv')

CDR2015_canonicalizing_distances = os.path.join(CDR2015_DIR_OUTPUT, 'canonicalizing_distances.tsv')
WORD2VEC_MODEL = '/home/kroll/workingdir/BioWordVec_PubMed_MIMICIII_d200.bin'

CDR2015_COLLECTION = 'CDR2015'
EXTRACT_PUBTATOR_DOCUMENTS = False
LOAD_PUBTATOR_DOCUMENT = False

RUN_CORENLP_OPENIE = False
RUN_PATHIE = False
RUN_STANZA_PATHIE = False
RUN_OPENIE6 = False

LOAD_STANZA_PATHIE = False
LOAD_CORENLP_OPENIE = False
LOAD_PATHIE = False
LOAD_OPENIE6 = False

CANONICALIZE_OUTPUT = False


def perform_cdr_evaluation(correct_relations, extraction_type):
    session = SessionExtended.get()
    q = session.query(Predication.document_id, Predication.subject_id, Predication.object_id) \
        .filter(Predication.document_collection == CDR2015_COLLECTION) \
        .filter(Predication.predicate_canonicalized == 'induces') \
        .filter(Predication.subject_type == CHEMICAL).filter(Predication.object_type == DISEASE) \
        .filter(Predication.extraction_type == extraction_type)

    extracted_induces = defaultdict(set)
    for r in session.execute(q):
        doc_id, subject_id, object_id = int(r[0]), r[1], r[2]
        extracted_induces[doc_id].add((subject_id, object_id))

    count_correct_extractions = 0
    count_wrong_extractions = 0
    for doc_id, extractions in extracted_induces.items():
        if doc_id in correct_relations:
            for s, o in extractions:
                if (s, o) in correct_relations[doc_id]:
                    count_correct_extractions += 1
                else:
                    count_wrong_extractions += 1
        else:
            count_wrong_extractions += len(extractions)

    count_missing_extractions = 0
    for doc_id, extractions in correct_relations.items():
        if doc_id in extracted_induces:
            for s, o in extractions:
                if (s, o) not in extracted_induces[doc_id]:
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

    logging.info('Loading extraction relations...')
    correct_relations = defaultdict(set)
    for doc in read_pubtator_documents(pubtator_doc_paths[0]):
        for line in doc.split('\n'):
            if '\tCID\t' in line:
                comps = line.split('\t')
                correct_relations[int(comps[0])].add((comps[2], comps[3]))

    if EXTRACT_PUBTATOR_DOCUMENTS:
        logging.info('Extracting documents...')
        with open(CDR2015_pubtator_extracted, 'wt') as f:
            for doc in read_pubtator_documents(pubtator_doc_paths[0]):
                doc_lines = []
                for line in doc.split('\n'):
                    if '\tCID\t' not in line:
                        doc_lines.append(f'{line}\n')

                doc_content = ''.join(doc_lines)
                tagged_doc = TaggedDocument(doc_content)
                f.write(str(tagged_doc))

    if LOAD_PUBTATOR_DOCUMENT:
        logging.info('Loading pubtator documents...')
        tagger_mapping = read_tagger_mapping(os.path.join(RESOURCE_DIR, "pubtator_central_taggermap.json"))
        tagger_list = list(tagger_mapping.values())
        tagger_list.append(UNKNOWN_TAGGER)
        insert_taggers(*tagger_list)
        document_bulk_load(CDR2015_pubtator_extracted, CDR2015_COLLECTION, tagger_mapping=tagger_mapping)

    if RUN_CORENLP_OPENIE:
        logging.info('Running StanfordCoreNLP...')
        run_corenlp_openie(CDR2015_pubtator_extracted, CDR2015_corenlp_openie_output)

    if LOAD_CORENLP_OPENIE:
        logging.info('Loading CoreNLP OpenIE extractions...')
        doc_ids, openie_tuples = read_stanford_openie_input(CDR2015_corenlp_openie_output)
        clean_open_ie(doc_ids, openie_tuples, CDR2015_COLLECTION)
        logging.info('finished')

    if RUN_PATHIE:
        logging.info('Running PathIE...')
        run_pathie(CDR2015_pubtator_extracted, CDR2015_pathie_output)

    if LOAD_PATHIE:
        logging.info('Reading extraction from tsv file...')
        predications = read_pathie_extractions_tsv(CDR2015_pathie_output)
        logging.info('{} extractions read'.format(len(predications)))
        insert_predications_into_db(predications, CDR2015_COLLECTION, extraction_type=PATHIE_EXTRACTION)
        logging.info('finished')

    if RUN_STANZA_PATHIE:
        logging.info('Running Stanza PathIE...')
        run_stanza_pathie(CDR2015_pubtator_extracted, CDR2015_stanza_pathie_output)

    if LOAD_STANZA_PATHIE:
        logging.info('Reading extraction from tsv file...')
        predications = read_pathie_extractions_tsv(CDR2015_stanza_pathie_output)
        logging.info('{} extractions read'.format(len(predications)))
        insert_predications_into_db(predications, CDR2015_COLLECTION, extraction_type=PATHIE_STANZA_EXTRACTION)
        logging.info('finished')

    if RUN_OPENIE6:
        logging.info('Running OpenIE6...')
        openie6_run(CDR2015_pubtator_extracted, CDR2015_openie6_output)

    if LOAD_OPENIE6:
        logging.info('Loading OpenIE 6.0 extractions...')
        doc_ids, openie_tuples = read_stanford_openie_input(CDR2015_openie6_output)
        clean_open_ie(doc_ids, openie_tuples, CDR2015_COLLECTION, extraction_type=OPENIE6_EXTRACTION)
        logging.info('finished')

    if CANONICALIZE_OUTPUT:
        logging.info('Canonicalizing output...')
        canonicalize_predication_table(WORD2VEC_MODEL, CDR2015_canonicalizing_distances,
                                       document_collection=CDR2015_COLLECTION,
                                       relation_vocabulary=create_predicate_vocab())
        check_type_constraints()

    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {PATHIE_EXTRACTION}...')
    perform_cdr_evaluation(correct_relations, PATHIE_EXTRACTION)
    logging.info('=' * 60)

    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {PATHIE_STANZA_EXTRACTION}...')
    perform_cdr_evaluation(correct_relations, PATHIE_STANZA_EXTRACTION)
    logging.info('=' * 60)

    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {OPENIE_EXTRACTION}...')
    perform_cdr_evaluation(correct_relations, OPENIE_EXTRACTION)
    logging.info('=' * 60)

    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {OPENIE6_EXTRACTION}...')
    perform_cdr_evaluation(correct_relations, OPENIE6_EXTRACTION)
    logging.info('=' * 60)


if __name__ == "__main__":
    main()
