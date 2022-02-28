import logging
import os
from collections import defaultdict
from datetime import datetime
from itertools import islice

from sqlalchemy import insert

from kgextractiontoolbox.extraction.loading.load_openie_extractions import clean_open_ie, read_stanford_openie_input, \
    OpenIEEntityFilterMode
from narraint.backend.database import SessionExtended
from narraint.backend.models import Document, Tag, Predication
from kgextractiontoolbox.cleaning.canonicalize_predicates import canonicalize_predication_table
from narraint.config import DATA_DIR
from kgextractiontoolbox.extraction.loading.load_pathie_extractions import read_pathie_extractions_tsv
from kgextractiontoolbox.extraction.openie.main import run_corenlp_openie
from kgextractiontoolbox.extraction.openie6.main import openie6_run
from kgextractiontoolbox.extraction.pathie.main import run_pathie
from kgextractiontoolbox.extraction.pathie_stanza.main import run_stanza_pathie
from kgextractiontoolbox.extraction.versions import PATHIE_EXTRACTION, PATHIE_STANZA_EXTRACTION, OPENIE6_EXTRACTION, \
    OPENIE_EXTRACTION
from kgextractiontoolbox.document.export import export
from narrant.preprocessing.enttypes import CHEMICAL, GENE
from narrant.progress import print_progress_with_eta

CHEMPROT_VOCABULARY = dict(
    upregulates=["upregulat*", "up regulat*", "up-regulat*", "stimulat*", "activat*", "increase", 'potentiate',
                 'induce'],
    inhibits=['downregulat*', 'down-regulat*', 'inhibit*', 'supress*', "decrease", "disrupt", "reduce"],
    agonist=['agonist activat*', 'agonist inhibt*', 'agoni*'],
    antagonist=["antagoni*"],
    substrate=['substrat*', 'metabolite', 'catalyze', 'express', 'synthesize', 'generate'],
    associated=['produc*', "contain", "convert", "yield", "isolate", "grow", "involve", 'mediate', 'convert',
                "occures", "evaluate", "augment", "effect", "develop", "affect", "contribute",
                "associated with", "isa", "same as", "coexists with", "process", "method of", "part of",
                "associate", "correlate", "play role", "play", "limit", "show", "present",
                "exhibit", "find", "form", "bind", "improve", 'alleviate', 'protect', 'abolish',
                'prevent', 'sensitize', 'regulate', 'act', 'modulate']
)

CHEMPROT_DIR = os.path.join(DATA_DIR, 'extraction/chemprot/processed')
# CHEMPROT_COLLECTION = 'ChemProtTrain'
# Test data:
CHEMPROT_COLLECTION = 'ChemProt'

CHEMPROT_DATASET = os.path.join(CHEMPROT_DIR, "test.tsv")
# CHEMPROT_DOCUMENTS = os.path.join(CHEMPROT_DIR, 'chemprot_test_abstracts_gs.tsv')
# CHEMPROT_TAGS_TSV = os.path.join(CHEMPROT_DIR, 'chemprot_test_entities_gs.tsv')
# CHEMPROT_RELATIONS_TSV = os.path.join(CHEMPROT_DIR, 'chemprot_test_relations_gs.tsv')

CHEMPROT_OUTPUT_DIR = os.path.join(CHEMPROT_DIR, 'output')

CHEMPROT_PUBTATOR = os.path.join(CHEMPROT_OUTPUT_DIR, 'documents.pubtator')
CHEMPROT_PATHIE_OUTPUT = os.path.join(CHEMPROT_OUTPUT_DIR, "pathie_V2.tsv")
CHEMPROT_PATHIE_STANZA_OUTPUT = os.path.join(CHEMPROT_OUTPUT_DIR, 'pathie_stanza_V2.tsv')

CHEMPROT_OPENIE_OUTPUT = os.path.join(CHEMPROT_OUTPUT_DIR, 'openie.tsv')
CHEMPROT_OPENIE6_OUTPUT = os.path.join(CHEMPROT_OUTPUT_DIR, 'openie6.tsv')

CP_canonicalizing_distances = os.path.join(CHEMPROT_OUTPUT_DIR, 'canonicalizing_distances.tsv')
WORD2VEC_MODEL = '/home/kroll/workingdir/BioWordVec_PubMed_MIMICIII_d200.bin'

CP_LOAD_DOCUMENTS_AND_TAGS = False
CP_EXPORT_PUBTATOR_DOCUMENTS = True

RUN_PATHIE = False
LOAD_PATHIE = False

RUN_STANZA_PATHIE = False
LOAD_STANZA_PATHIE = False

RUN_CORENLP_OPENIE = False
LOAD_CORENLP_OPENIE = False

RUN_OPENIE6 = False
LOAD_OPENIE6 = False

CANONICALIZE_OUTPUT = False


def perform_chemprot_evaluation(correct_relations, extraction_type, relations):
    session = SessionExtended.get()
    q = session.query(Predication.document_id, Predication.relation,
                      Predication.subject_id, Predication.object_id) \
        .filter(Predication.document_collection == CHEMPROT_COLLECTION) \
        .filter(Predication.relation.in_(relations)) \
        .filter(Predication.subject_type == CHEMICAL) \
        .filter(Predication.object_type == GENE) \
        .filter(Predication.extraction_type == extraction_type)

    extracted_relations = defaultdict(set)
    for r in session.execute(q):
        doc_id, relation, subject_id, object_id = int(r[0]), r[1], r[2], r[3]
        extracted_relations[doc_id].add(relation)

    count_correct_extractions = 0
    count_wrong_extractions = 0
    wrong_found_ids = set()
    for doc_id, extractions in extracted_relations.items():
        if doc_id in correct_relations:
            for p in extractions:
                if p in correct_relations[doc_id]:
                    count_correct_extractions += 1
                else:
                    wrong_found_ids.add(doc_id)
                    count_wrong_extractions += 1
        else:
            wrong_found_ids.add(doc_id)
            count_wrong_extractions += len(extractions)

    missed_ids = set()
    count_missing_extractions = 0
    for doc_id, extractions in correct_relations.items():
        if doc_id in extracted_relations:
            for p in extractions:
                if p not in extracted_relations[doc_id]:
                    missed_ids.add(doc_id)
                    count_missing_extractions += 1
        else:
            missed_ids.add(doc_id)
            count_missing_extractions += len(extractions)

    if count_correct_extractions > 0:
        precision = count_correct_extractions / (count_correct_extractions + count_wrong_extractions)
        recall = count_correct_extractions / (count_correct_extractions + count_missing_extractions)
        f1 = (2 * precision * recall) / (precision + recall)
    else:
        precision, recall, f1 = 0.0, 0.0, 0.0
    wrong_str = ', '.join([str(i) for i in wrong_found_ids])
    missed_str = ', '.join([str(i) for i in missed_ids])
    logging.info(f'wrong: ({wrong_str})')
    logging.info(f'missed: ({missed_str})')
    logging.info(f'Precision: {precision}')
    logging.info(f'Recall: {recall}')
    logging.info(f'F1-measure: {f1} ')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    if not os.path.isdir(CHEMPROT_OUTPUT_DIR):
        os.makedirs(CHEMPROT_OUTPUT_DIR)

    logging.info(f'Loading dataset: {CHEMPROT_DATASET}...')
    id2docid, id2sentence, id2relation = {}, {}, {}
    with open(CHEMPROT_DATASET, 'rt') as f:
        for idx, line in enumerate(islice(f, 1, None)):
            document, sentence, relation = line.strip().split('\t')
            document_id = int(document.split('.')[0])
            id2docid[idx] = document_id
            id2sentence[idx] = sentence.strip()
            id2relation[idx] = relation.strip()

    if CP_LOAD_DOCUMENTS_AND_TAGS:
        logging.info('Loading documents...')
        session = SessionExtended.get()
        start_time = datetime.now()
        for idx, (document_id, sentence) in enumerate(id2sentence.items()):
            print_progress_with_eta('loading documents', idx, len(id2sentence), start_time, print_every_k=100)
            sentence = sentence.replace('@CHEMICAL$', '@Chemical')
            sentence = sentence.replace('@GENE$', '@Gene')
            insert_document = insert(Document).values(
                collection=CHEMPROT_COLLECTION,
                id=document_id,
                title=sentence,
                abstract="T",
            )
            session.execute(insert_document)

            chemical_pos = sentence.find('@Chemical')
            insert_chemical = insert(Tag).values(
                ent_type=CHEMICAL,
                start=chemical_pos,
                end=chemical_pos + len('@Chemical'),
                ent_id=CHEMICAL,
                ent_str='@Chemical',
                document_id=document_id,
                document_collection=CHEMPROT_COLLECTION,
            )
            session.execute(insert_chemical)

            gene_pos = sentence.find('@Gene')
            insert_chemical = insert(Tag).values(
                ent_type=GENE,
                start=gene_pos,
                end=gene_pos + len('@Gene'),
                ent_id=GENE,
                ent_str="@Gene",
                document_id=document_id,
                document_collection=CHEMPROT_COLLECTION,
            )
            session.execute(insert_chemical)

        logging.info('Commit loading...')
        session.commit()

    if CP_EXPORT_PUBTATOR_DOCUMENTS:
        logging.info(f'Exporting ChemProt PubTator documents... ({CHEMPROT_PUBTATOR})')
        export(CHEMPROT_PUBTATOR, [CHEMICAL, GENE], collection=CHEMPROT_COLLECTION)

    if RUN_PATHIE:
        logging.info('Running PathIE...')
        run_pathie(CHEMPROT_PUBTATOR, CHEMPROT_PATHIE_OUTPUT, predicate_vocabulary=CHEMPROT_VOCABULARY)

    if LOAD_PATHIE:
        logging.info('Reading extraction from tsv file...')
        predications = read_pathie_extractions_tsv(CHEMPROT_PATHIE_OUTPUT)
        logging.info('{} extractions read'.format(len(predications)))
        insert_predications_into_db(predications, CHEMPROT_COLLECTION, extraction_type=PATHIE_EXTRACTION,
                                    clean_genes=False)
        logging.info('finished')

    if RUN_STANZA_PATHIE:
        logging.info('Running Stanza PathIE...')
        run_stanza_pathie(CHEMPROT_PUBTATOR, CHEMPROT_PATHIE_STANZA_OUTPUT, predicate_vocabulary=CHEMPROT_VOCABULARY)

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
        clean_open_ie(doc_ids, openie_tuples, CHEMPROT_COLLECTION, entity_filter=OpenIEEntityFilterMode.PARTIAL_ENTITY_FILTER)
        logging.info('finished')

    if RUN_OPENIE6:
        logging.info('Running OpenIE6...')
        openie6_run(CHEMPROT_PUBTATOR, CHEMPROT_OPENIE6_OUTPUT)

    if LOAD_OPENIE6:
        logging.info('Loading OpenIE 6.0 extractions...')
        doc_ids, openie_tuples = read_stanford_openie_input(CHEMPROT_OPENIE6_OUTPUT)
        clean_open_ie(doc_ids, openie_tuples, CHEMPROT_COLLECTION, extraction_type=OPENIE6_EXTRACTION, entity_filter=OpenIEEntityFilterMode.PARTIAL_ENTITY_FILTER)
        logging.info('finished')

    if CANONICALIZE_OUTPUT:
        logging.info('Canonicalizing output...')
        canonicalize_predication_table(WORD2VEC_MODEL, CP_canonicalizing_distances,
                                       relation_vocabulary=CHEMPROT_VOCABULARY,
                                       document_collection=CHEMPROT_COLLECTION,
                                       min_predicate_threshold=0)
        # clean_extractions_in_database()

    logging.info('Loading correct relations...')
    gold_relations = defaultdict(set)
    for document_id, relation in id2relation.items():
        if relation == 'CPR:4':
            gold_relations[document_id].add('inhibits')
        if relation == 'CPR:3':
            gold_relations[document_id].add('upregulates')
        if relation == 'CPR:5':
            gold_relations[document_id].add('agonist')
        if relation == 'CPR:6':
            gold_relations[document_id].add('antagonist')
        if relation == 'CPR:9':
            gold_relations[document_id].add('substrate')

    for predicate in ['inhibits', 'upregulates', 'agonist', 'antagonist', 'substrate']:
        gold_relations_for_type = {k: v for k, v in gold_relations.items() if predicate in v}
        logging.info(f'Checking {predicate}')

        logging.info('=' * 60)
        logging.info(f'Begin evaluation for {PATHIE_EXTRACTION}...')
        perform_chemprot_evaluation(gold_relations_for_type, PATHIE_EXTRACTION, [predicate])
        logging.info('=' * 60)

        logging.info('=' * 60)
        logging.info(f'Begin evaluation for {PATHIE_STANZA_EXTRACTION}...')
        perform_chemprot_evaluation(gold_relations_for_type, PATHIE_STANZA_EXTRACTION, [predicate])
        logging.info('=' * 60)

        logging.info('=' * 60)
        logging.info(f'Begin evaluation for {OPENIE_EXTRACTION}...')
        perform_chemprot_evaluation(gold_relations_for_type, OPENIE_EXTRACTION, [predicate])
        logging.info('=' * 60)

        logging.info('=' * 60)
        logging.info(f'Begin evaluation for {OPENIE6_EXTRACTION}...')
        perform_chemprot_evaluation(gold_relations_for_type, OPENIE6_EXTRACTION, [predicate])
        logging.info('=' * 60)

    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {PATHIE_EXTRACTION}...')
    perform_chemprot_evaluation(gold_relations, PATHIE_EXTRACTION,
                                ['inhibits', 'upregulates', 'agonist', 'antagonist', 'substrate'])

    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {PATHIE_STANZA_EXTRACTION}...')
    perform_chemprot_evaluation(gold_relations, PATHIE_STANZA_EXTRACTION,
                                ['inhibits', 'upregulates', 'agonist', 'antagonist', 'substrate'])
    logging.info('=' * 60)

    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {OPENIE_EXTRACTION}...')
    perform_chemprot_evaluation(gold_relations, OPENIE_EXTRACTION,
                                ['inhibits', 'upregulates', 'agonist', 'antagonist', 'substrate'])
    logging.info('=' * 60)

    logging.info('=' * 60)
    logging.info(f'Begin evaluation for {OPENIE6_EXTRACTION}...')
    perform_chemprot_evaluation(gold_relations, OPENIE6_EXTRACTION,
                                ['inhibits', 'upregulates', 'agonist', 'antagonist', 'substrate'])
    logging.info('=' * 60)


if __name__ == "__main__":
    main()
