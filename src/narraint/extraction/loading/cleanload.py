import logging
from collections import namedtuple
from datetime import datetime
from typing import List
import hashlib
from io import StringIO

from narraint.config import BULK_INSERT_AFTER_K
from narrant.entity.meshontology import MeSHOntology
from narrant.entity.entityresolver import GeneResolver
from narrant.preprocessing.enttypes import GENE
from narraint.backend.models import Predication, Sentence
from narraint.backend.database import SessionExtended
from narrant.progress import print_progress_with_eta

MAX_SENTENCE_LENGTH = 1000
MIN_SUBJECT_OR_OBJECT_LEN = 3

# A list of words to ignore in OpenIE extractions
TOKENS_TO_IGNORE = {'with', 'by', 'of', 'from', 'to', 'than', 'as', 'on', 'at', 'may', 'in', 'can', 'more', 'less',
                    'into', 'be', 'have', 'well', 'for'}

PRED = namedtuple('Predication', ['doc_id', 'subj', 'pred', 'pred_cleaned', 'obj', 'conf', 'sent', 's_id', 's_str',
                                  's_type', 'o_id', 'o_str', 'o_type'])


def clean_and_translate_gene_ids(predications: List[PRED]):
    """
     Some extractions may contain several gene ids (these gene ids are encoded as "id1;id2;id3" as tags)
     This method splits these extraction in single facts with only a single gene id for each
     Gene IDs are unique for each species - We are only interested in the names of genes
     Thus, we map each gene id to its gene symbol, so that, e.g. CYP3A4 is the unique description for all species
     :param predications: a list of predications
     :return: a list of cleaned predications
     """
    logging.info('Cleaning and translating gene ids...')
    predications_cleaned = []
    generesolver = GeneResolver()
    generesolver.load_index()
    start_time = datetime.now()
    predications_len = len(predications)
    for idx, p in enumerate(predications):
        subj_ids = set()
        if p.s_type == GENE:
            if ';' in p.s_id:
                for g_id in p.s_id.split(';'):
                    try:
                        subj_ids.add(generesolver.gene_id_to_symbol(g_id).lower())
                    except (KeyError, ValueError):
                        continue
            else:
                try:
                    subj_ids.add(generesolver.gene_id_to_symbol(p.s_id).lower())
                except (KeyError, ValueError):
                    continue
        else:
            subj_ids = [p.s_id]
        obj_ids = set()
        if p.o_type == GENE:
            if ';' in p.o_id:
                for g_id in p.o_id.split(';'):
                    try:
                        obj_ids.add(generesolver.gene_id_to_symbol(g_id).lower())
                    except (KeyError, ValueError):
                        continue
            else:
                try:
                    obj_ids.add(generesolver.gene_id_to_symbol(p.o_id).lower())
                except (KeyError, ValueError):
                    continue
        else:
            obj_ids = [p.o_id]
        for s_id in subj_ids:
            for o_id in obj_ids:
                p_cleaned = PRED(p.doc_id, p.subj, p.pred, p.pred_cleaned, p.obj, p.conf, p.sent, s_id, p.s_str,
                                 p.s_type, o_id, p.o_str, p.o_type)
                predications_cleaned.append(p_cleaned)
        print_progress_with_eta('cleaning gene ids...', idx, predications_len, start_time)
    logging.info('{} predications obtained'.format(len(predications_cleaned)))
    return predications_cleaned


def text_to_md5hash(text: str) -> str:
    """
    Converts a arbitrary string to a md5 hash
    :param text: some string
    :return: a string consisting of md5 hexdigest
    """
    return hashlib.md5(text.encode()).hexdigest()


def load_sentences_with_hashes(document_collection: str):
    """
    Loads all sentences with the corresponding hashes from the database
    :param document_collection: the document collection
    :return: a dict mapping md5hashes to a sentence id
    """
    logging.info('Retrieving known sentences for collection...')
    session = SessionExtended.get()
    sentence_q = session.query(Sentence.id, Sentence.md5hash).filter(Sentence.document_collection == document_collection)
    hash2sentence = {}
    for sent in sentence_q:
        hash2sentence[sent[1]] = sent[0]
    logging.info(f'{len(hash2sentence)} sentences retrieved')
    return hash2sentence


def load_highest_sentence_id() -> int:
    """
    Finds the highest sentence id in the sentence table
    :return: highest used sentence id
    """
    session = SessionExtended.get()
    sentence_id = 0
    for q in session.execute(session.query(Sentence.id).order_by(Sentence.id.desc()).limit(1)):
        sentence_id = q[0]
    return sentence_id


def clean_sentence_str(sentence: str) -> str:
    """
    Postgres is not able to handle sentences containing a null-terminating char or characters starting by backslash x
    This method cleans the sentences (replace all \ by \\)
    :param sentence: the sentence to clean
    :return: a cleaned version of the sentence
    """
    if len(sentence) > MAX_SENTENCE_LENGTH:
        sentence = sentence[0:MAX_SENTENCE_LENGTH]
    return sentence.replace('\t', ' ').replace('\n', ' ').replace('\\', '\\\\')


def clean_predications(tuples_cleaned: List[PRED], collection, extraction_type, clean_genes=True):
    """
    Cleans a list of predications based on a set of filters
    :param tuples_cleaned: a list of PRED tuples
    :param collection: the document collection
    :param extraction_type: extraction type like OpenIE or PathIE
    :param clean_genes: if true the genes will be cleaned (multiple genes are split and ids are translated to symbols)
    :return: a list of sentence objects to insert, a list of predication values to insert
    """
    if clean_genes:
        tuples_cleaned = clean_and_translate_gene_ids(tuples_cleaned)
    hash2sentence = load_sentences_with_hashes(collection)
    sentid2hash = {v: k for k, v in hash2sentence.items()}
    inserted_sentence_ids = set([k for k in sentid2hash.keys()])

    last_highest_sentence_id = load_highest_sentence_id()
    logging.info(f'Last highest sentence_id was: {last_highest_sentence_id}')
    logging.info(f'Querying duplicates from database (collection: {collection} and extraction type: {extraction_type})')

    logging.info('Check duplicates only within this session...')
    duplicate_check = set()

    last_highest_sentence_id += 1
    len_tuples = len(tuples_cleaned)
    logging.info('Inserting {} tuples to database...'.format(len_tuples))
    start_time = datetime.now()
    predication_values = []
    sentence_values = []
    for i, p in enumerate(tuples_cleaned):
        sentence_txt = p.sent.replace('\n', '')
        # Todo: Very dirty fix here
        if len(p.s_str) < MIN_SUBJECT_OR_OBJECT_LEN or len(p.o_str) < MIN_SUBJECT_OR_OBJECT_LEN:
            continue
        # Todo: dirty fix here empty id or ner id
        if p.s_id == '-' or p.o_id == '-' or not p.s_id.strip() or not p.o_id.strip():
            continue
        # Clean dirty predicates (only one character)
        if len(p.pred_cleaned) < 2:
            continue

        sent_hash = text_to_md5hash(sentence_txt)
        key = (p.doc_id, p.s_id, p.s_type, p.pred_cleaned, p.o_id, p.o_type, sent_hash)
        if key in duplicate_check:
            continue
        duplicate_check.add(key)

        sentence_id = -1
        if sent_hash in hash2sentence:
            sentence_id = hash2sentence[sent_hash]
        # no sentence_id found
        else:
            sentence_id = last_highest_sentence_id
            hash2sentence[sent_hash] = sentence_id
            last_highest_sentence_id += 1

        predication_values.append(dict(
            document_id=p.doc_id,
            document_collection=collection,
            subject_id=p.s_id,
            subject_str=clean_sentence_str(p.s_str),
            subject_type=p.s_type,
            predicate=p.pred_cleaned,
            object_id=p.o_id,
            object_str=clean_sentence_str(p.o_str),
            object_type=p.o_type,
            confidence=p.conf,
            sentence_id=sentence_id,
            extraction_type=extraction_type
        ))

        # check whether the sentence was inserted before
        if sentence_id not in inserted_sentence_ids:
            inserted_sentence_ids.add(sentence_id)
            sentence_values.append((dict(
                id=sentence_id,
                document_id=p.doc_id,
                document_collection=collection,
                text=clean_sentence_str(sentence_txt),
                md5hash=sent_hash)))

        print_progress_with_eta("Preparing data...", i, len_tuples, start_time)
    return predication_values, sentence_values


def postgres_clean_and_export_predications_to_copy_load_tsv(predication_values, sentence_values):
    """
    insert a list of cleaned tuples into the database (bulk insert)
    does not check for collisions
    :param predication_values: list of predication values
    :param sentence_values: list of sentence values
    :return: Nothing
    """
    sentence_values_len = len(sentence_values)
    predication_values_len = len(predication_values)
    session = SessionExtended.get()
    connection = session.connection().connection
    if sentence_values_len > 0:
        logging.info(f'Exporting {len(sentence_values)} sentences to memory file')
        sent_keys = ["id", "document_id", "document_collection", "text", "md5hash"]
        f_sent = StringIO()
        for idx, sent_value in enumerate(sentence_values):
            sent_str = '{}'.format('\t'.join([str(sent_value[k]) for k in sent_keys]))
            if idx == 0:
                f_sent.write(sent_str)
            else:
                f_sent.write(f'\n{sent_str}')
        # free memory here
        sentence_values.clear()

        cursor = connection.cursor()
        logging.info('Executing copy from sentence...')
        f_sent.seek(0)
        cursor.copy_from(f_sent, 'Sentence', sep='\t', columns=sent_keys)
        logging.info('Committing...')
        connection.commit()
        f_sent.close()

    if predication_values_len > 0:
        logging.info(f'Exporting {len(predication_values)} predications to memory file')
        pred_keys = ['document_id', 'document_collection', 'subject_id', 'subject_str', 'subject_type', 'predicate',
                     'object_id', 'object_str', 'object_type', 'confidence', 'sentence_id', 'extraction_type']

        f_pred = StringIO()
        for idx, pred_val in enumerate(predication_values):
            pred_str = '{}'.format('\t'.join([str(pred_val[k]) for k in pred_keys]))
            if idx == 0:
                f_pred.write(pred_str)
            else:
                f_pred.write(f'\n{pred_str}')
        # free memory here
        predication_values.clear()

        logging.info('Executing copy from predication...')
        cursor = connection.cursor()
        f_pred.seek(0)
        cursor.copy_from(f_pred, 'Predication', sep='\t', columns=pred_keys)
        logging.info('Committing...')
        connection.commit()
        f_pred.close()
        logging.info(f'Finished {sentence_values_len} sentences and {predication_values_len} predications have been '
                     f'inserted')


def insert_predications_into_db(predication_values, sentence_values):
    """
    Insert predication and sentence values to db
    :param predication_values: a list of predication values
    :param sentence_values: a list of sentence values
    :return: None
    """
    session = SessionExtended.get()
    # use fast postgres insert if possible
    if SessionExtended.is_postgres:
        postgres_clean_and_export_predications_to_copy_load_tsv(predication_values, sentence_values)
    else:
        sentence_part = []
        logging.info('Inserting sentences...')
        len_tuples = len(sentence_values)
        start_time = datetime.now()
        for i, s in enumerate(sentence_values):
            sentence_part.append(s)
            if i % BULK_INSERT_AFTER_K == 0:
                session.bulk_insert_mappings(Sentence, sentence_part)
                session.commit()
                sentence_part.clear()
            print_progress_with_eta("Inserting sentences...", i, len_tuples, start_time)
        session.bulk_insert_mappings(Sentence, sentence_part)
        session.commit()
        sentence_part.clear()

        predication_part = []
        logging.info('Inserting predications...')
        len_tuples = len(predication_values)
        start_time = datetime.now()
        for i, p in enumerate(predication_values):
            predication_part.append(p)
            if i % BULK_INSERT_AFTER_K == 0:
                session.bulk_insert_mappings(Predication, predication_part)
                session.commit()
                predication_part.clear()
            print_progress_with_eta("Inserting predications...", i, len_tuples, start_time)
        session.bulk_insert_mappings(Predication, predication_part)
        session.commit()
        predication_part.clear()
        logging.info('Insert finished ({} facts inserted)'.format(len_tuples))


def clean_and_load_predications_into_db(tuples_cleaned: List[PRED], collection, extraction_type, clean_genes=True):
    """
     insert a list of cleaned tuples into the database (bulk insert)
     does not check for collisions
     :param tuples_cleaned: a list of PRED tuples
     :param collection: the document collection
     :param extraction_type: extraction type like OpenIE or PathIE
     :param clean_genes: if true the genes will be cleaned (multiple genes are split and ids are translated to symbols)
     :return: Nothing
     """
    predication_values, sentence_values = clean_predications(tuples_cleaned, collection, extraction_type,
                                                             clean_genes=clean_genes)
    logging.info(f'{len(predication_values)} predications and {len(sentence_values)} sentences to insert...')
    insert_predications_into_db(predication_values, sentence_values)

