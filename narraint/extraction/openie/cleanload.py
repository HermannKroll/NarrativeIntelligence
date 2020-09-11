import argparse
import logging
from collections import namedtuple, defaultdict
from datetime import datetime
from typing import List
import hashlib
import nltk

from nltk.corpus import wordnet
from sqlalchemy.exc import IntegrityError

from narraint.entity.meshontology import MeSHOntology
from narraint.entity.entityresolver import GeneResolver
from narraint.entity.enttypes import GENE, DISEASE, CHEMICAL, DOSAGE_FORM
from narraint.backend.models import Tag, Predication, Sentence
from narraint.backend.database import Session
from narraint.extraction.versions import OPENIE_VERSION, OPENIE_EXTRACTION
from narraint.progress import print_progress_with_eta

BULK_INSERT_AFTER_K = 10000
MAX_SENTENCE_LENGTH = 3000

# A list of words to ignore in OpenIE extractions
TOKENS_TO_IGNORE = {'with', 'by', 'of', 'from', 'to', 'than', 'as', 'on', 'at', 'may', 'in', 'can', 'more', 'less',
                    'into', 'be', 'have', 'well', 'for'}


PRED = namedtuple('Predication', ['doc_id', 'subj', 'pred', 'pred_cleaned', 'obj', 'conf', 'sent', 's_id', 's_str',
                                  's_type', 'o_id', 'o_str', 'o_type'])
OPENIE_TUPLE = namedtuple("OpenIETuple", ['doc_id', 'subj', 'pred', 'pred_lemma', 'obj', 'conf', 'sent'])


def read_stanford_openie_input(openie_file: str):
    """
    reads a OpenIE output file created by main.py and transforms the data into a list of
    OpenIE tuples
    :param openie_file: OpenIE output file created by main.py
    :return: a set of document ids, a list of OpenIE tuples
    """
    doc_ids = set()
    tuples_cached = []
    logging.info('Reading OpenIE input...')
    # open the input open ie file
    with open(openie_file, 'r') as f:
        # read all lines for a single doc
        for line in f:
            c = line.strip().split("\t")
            o_t = OPENIE_TUPLE(int(c[0]), c[1], c[2], c[3], c[4], c[5], c[6])
            doc_ids.add(o_t.doc_id)
            tuples_cached.append(o_t)
    return doc_ids, tuples_cached


def clean_sentence(sentence: str):
    """
    Clean OpenIE sentences by replacing the bracket shortcuts back to valid brackets
    :param sentence: a sentence
    :return: cleaned sentence
    """
    s = sentence.replace('-LRB- ', '(')
    s = s.replace('-LSB- ', '(')
    s = s.replace(' -RRB-', ')')
    s = s.replace(' -RSB-', ')')
    return s


def get_subject_and_object_entities(doc_tags, sub: str, obj: str):
    """
    Computes a list of entities which are included in the subject as well as a list of entities
    included in the object
    :param doc_tags: a dictionary mapping a doc_id to tags
    :param sub: the subject
    :param obj: the object
    :return: a list of entities (ent_str, ent_id, ent_type) included in subj, list of entities in obj
    """
    # default not hit
    subs_included = []
    objs_included = []
    # compute lower case with empty spaces
    if sub[-1].isalpha():
        sub_text = ' {} '.format(sub.lower())
    else:
        sub_text = ' {} '.format(sub.lower()[0:-1])

    if obj[-1].isalpha():
        obj_text = ' {} '.format(obj.lower())
    else:
        obj_text = ' {} '.format(obj.lower()[0:-1])

    # check if an entity occurs within the sentence
    for ent_id, ent_str, ent_type in doc_tags:
        # skip empty mesh ids
        if ent_id == '-1' or ent_id == '':
            continue

        if ent_str in sub_text:
            s_t = (ent_str, ent_id, ent_type)
            subs_included.append(s_t)
        if ent_str in obj_text:
            o_t = (ent_str, ent_id, ent_type)
            objs_included.append(o_t)

    return subs_included, objs_included


def load_tags_for_doc_ids(doc_ids, collection):
    """
    loads the database entity tags for a list of doc_ids
    :param doc_ids: sequence of doc_ids
    :param collection: document collection
    :return: a dict mapping document ids to tuples (ent_id, ent_str, ent_type)
    """
    session = Session.get()
    # get all tags for the given doc_ids
    query = session.query(Tag.document_id, Tag.ent_id, Tag.ent_str, Tag.ent_type)
    query = query.filter(Tag.document_collection == collection)
    query = query.filter(Tag.document_id.in_(doc_ids))

    doc2tags = defaultdict(list)
    results = session.execute(query)
    counter = 0
    for row in results:
        ent_str = ' {} '.format(row[2]).lower()
        t = (row[1], ent_str, row[3])
        doc2tags[int(row[0])].append(t)
        counter += 1
    logging.info('{} tags load from db'.format(counter))
    return doc2tags


def _insert_predication_skip_duplicates(session, predication_values):
    session.rollback()
    session.commit()
    for value in predication_values:
        try:
            session.bulk_insert_mappings(Predication, [value])
            session.commit()
        except IntegrityError:
            session.rollback()
            session.commit()
            logging.warning('Skip duplicated fact: ({}, {}, {}, {}, {}, {})'.
                            format(value["document_id"], value["document_collection"], value["subject_id"],
                                   value["predicate"], value["object_id"], value["sentence_id"]))


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


def transform_mesh_ids_to_prefixes(predications: List[PRED]):
    """
    Transforms the MeSH ids of all facts to MeSH tree numbers
    If a descriptor has multiple tree numbers, the fact will be duplicated
    :param predications: a list of predications
    :return: a list of transformed predications
    """
    logging.info('Transforming entity ids to prefixes...')
    predications_cleaned = []
    mesh_ontology = MeSHOntology.instance()
    start_time = datetime.now()
    predications_len = len(predications)
    for idx, p in enumerate(predications):
        subj_ids = set()
        if p.s_type in [CHEMICAL, DISEASE, DOSAGE_FORM] and p.s_id.startswith('MESH:'):
            try:
                subj_ids.update(mesh_ontology.get_tree_numbers_for_descriptor(p.s_id[5:]))
            except KeyError:
                subj_ids.add(p.s_id)
        else:
            subj_ids = [p.s_id]
        obj_ids = set()
        if p.o_type in [CHEMICAL, DISEASE, DOSAGE_FORM] and p.o_id.startswith('MESH:'):
            try:
                obj_ids.update(mesh_ontology.get_tree_numbers_for_descriptor(p.o_id[5:]))
            except KeyError:
                obj_ids.add(p.o_id)
        else:
            obj_ids = [p.o_id]
        for s_id in subj_ids:
            for o_id in obj_ids:
                p_cleaned = PRED(p.doc_id, p.subj, p.pred, p.pred_cleaned, p.obj, p.conf, p.sent, s_id, p.s_str,
                                 p.s_type, o_id, p.o_str, p.o_type)
                predications_cleaned.append(p_cleaned)
        print_progress_with_eta('transforming mesh ids to tree prefixes...', idx, predications_len, start_time)
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
    :return: a default dict mapping md5hashes to (sentence_id, sentence_text) tuples
    """
    logging.info('Retrieving known sentences for collection...')
    session = Session.get()
    sentence_q = session.query(Sentence).filter(Sentence.document_collection == document_collection)
    hash2sentence = defaultdict(list)
    count = 0
    for sent in sentence_q:
        hash2sentence[sent.md5hash].append((sent.id, sent.text))
        count += 1
    logging.info('{} sentences retrieved'.format(count))
    return hash2sentence


def insert_sentence_and_get_sentence_id(session, sentence_txt: str, hash2sentence, document_id, document_collection):
    """
    Checks whether the sentence is already contained in the database -> return the known sentence id
    :param session: current db session
    :param sentence_txt: the sentence text to insert
    :param hash2sentence: the defaultdict mapping md5hashes to (sentence_id, sentence_text) tuples
    :param document_id: the document id for the sentence
    :param document_collection: the document collection for the sentence
    :return:
    """
    sentence_hash = text_to_md5hash(sentence_txt)
    if sentence_hash in hash2sentence:
        for s_id, s_txt in hash2sentence[sentence_hash]:
            if sentence_txt == s_txt:
                return s_id
    # we have to insert a new sentence
    sentence = Sentence(document_id=document_id, document_collection=document_collection, text=sentence_txt,
                        md5hash=sentence_hash)
    session.add(sentence)
    session.flush()
    session.refresh(sentence)
    hash2sentence[sentence_hash].append((sentence.id, sentence.text))
    return sentence.id


def insert_predications_into_db(tuples_cleaned: List[PRED], collection, extraction_type, version, clean_genes=True,
                                do_transform_mesh_ids_to_prefixes=True):
    """
    insert a list of cleaned tuples into the database (bulk insert)
    does not check for collisions
    :param tuples_cleaned: a list of PRED tuples
    :param collection: the document collection
    :param extraction_type: extraction type like OpenIE or PathIE
    :param version: version of extraction method
    :param clean_genes: if true the genes will be cleaned (multiple genes are split and ids are translated to symbols)
    :param do_transform_mesh_ids_to_prefixes: if true all MeSH ids will be translated to MeSH tree numbers
    :return: Nothing
    """
    if clean_genes:
        tuples_cleaned = clean_and_translate_gene_ids(tuples_cleaned)
    if do_transform_mesh_ids_to_prefixes:
        tuples_cleaned = transform_mesh_ids_to_prefixes(tuples_cleaned)
    hash2sentence = load_sentences_with_hashes(collection)
    session = Session.get()
    len_tuples = len(tuples_cleaned)
    logging.info('Inserting {} tuples to database...'.format(len_tuples))
    start_time = datetime.now()
    predication_values = []
    duplicate_check = set()
    for i, p in enumerate(tuples_cleaned):
        key = (p.doc_id, p.s_id, p.s_type, p.pred, p.o_id, p.o_type, p.sent)
        if key in duplicate_check:
            continue
        duplicate_check.add(key)
        predication_values.append(dict(
            document_id=p.doc_id,
            document_collection=collection,
            subject_id=p.s_id,
            subject_str=p.s_str,
            subject_type=p.s_type,
            predicate=p.pred_cleaned,
            object_id=p.o_id,
            object_str=p.o_str,
            object_type=p.o_type,
            confidence=p.conf,
            sentence_id=insert_sentence_and_get_sentence_id(session, p.sent, hash2sentence, p.doc_id, collection),
            extraction_type=extraction_type
        ))
        try:
            if i % BULK_INSERT_AFTER_K == 0:
                session.bulk_insert_mappings(Predication, predication_values)
                session.commit()
                predication_values.clear()
        except IntegrityError:
            _insert_predication_skip_duplicates(session, predication_values)
            predication_values.clear()

        print_progress_with_eta("Inserting", i, len_tuples, start_time)
    try:
        session.bulk_insert_mappings(Predication, predication_values)
        session.commit()
    except IntegrityError:
        _insert_predication_skip_duplicates(session, predication_values)
        predication_values.clear()
    logging.info('Insert finished ({} facts inserted)'.format(len(tuples_cleaned)))


def _clean_tuple_predicate_based(t: PRED):
    """
    cleans the tuple based on predicate rules
    1. remove unnecessary tokens
    2. passive voice -> active voice
    3. remove be and have predicates
    4. apply stripping to all fields
    :param t: a tuple (named tuple PRED expected, PRED.pred_cleaned is expected to be the a lemmatized predicate)
    :return: a cleaned tuple (PRED)
    """
    fact_sentence = '{} {} {}.'.format(t.subj, t.pred, t.obj)
    fact_sentence_tokens = nltk.word_tokenize(fact_sentence)
    pos_tags = nltk.pos_tag(fact_sentence_tokens)

    # ignore tuples from too long sentences
    if len(t.sent) > MAX_SENTENCE_LENGTH:
        return None
    # pred_lemma is stored in the pred_cleaned field
    pred_lemma = t.pred_cleaned

    # ignore tuples containing just 'be' and 'have'
    if pred_lemma == 'be' or pred_lemma == 'have':
        return None

    pred_cleaned = ''
    # remove be and have if multiple tokens are included
    tokens = pred_lemma.split(' ')
    start_pred = len(t.subj.split(' '))
    participe_past_detected = False
    for idx, tok in enumerate(tokens):
        pos_tag = pos_tags[start_pred + idx][1]
        if pos_tag == 'VBN':
            participe_past_detected = True

        # remove unnecessary phrases
        if tok in TOKENS_TO_IGNORE:
            continue
        # remove adjectives and adverbs
        syns = wordnet.synsets(tok)
        if len(syns) > 0 and syns[0].pos() in ['a', 's', 'r']:
            continue

        pred_cleaned += tok + ' '

    # clean the sentence
    cleaned_sentence = clean_sentence(t.sent).strip()
    # check for active and passive voice
    if ('be' in tokens and participe_past_detected) or ('by' in t.pred and participe_past_detected):
        # passive means we have to change the direction of the tuple
        t_sub, t_s_txt, t_s_id, t_s_type = t.subj, t.s_str, t.s_id, t.s_type
        subj, s_txt, s_id, s_type = t.obj, t.o_str, t.o_id, t.o_type
        obj, o_txt, o_id, o_type = t_sub, t_s_txt, t_s_id, t_s_type

        return PRED(t.doc_id, subj.strip(), t.pred.strip(), pred_cleaned.strip(), obj.strip(), t.conf, cleaned_sentence,
                    s_id, s_txt.strip(), s_type.strip(), o_id, o_txt.strip(), o_type.strip())

    return PRED(t.doc_id, t.subj.strip(), t.pred.strip(), pred_cleaned.strip(), t.obj.strip(), t.conf, cleaned_sentence,
                t.s_id, t.s_str.strip(), t.s_type.strip(), t.o_id, t.o_str.strip(), t.o_type.strip())


def clean_open_ie(doc_ids, openie_tuples: [OPENIE_TUPLE], collection):
    """
    cleans the open ie tuples by:
    1. applying an entity filter (keep only facts about entities)
    2. cleaning predicates (remove be and have & change passive voice to active voice & remove tokens see above)
    :param doc_ids: a set of document ids
    :param openie_tuples: a list of openie tuples
    :param collection: document collection where the id's stem from (to retrieve entities from the database)
    :return:
    """
    logging.info('Beginning cleaning step...')
    tuples_cached = openie_tuples
    logging.info('{} OpenIE tuples read...'.format(len(tuples_cached)))
    if len(doc_ids) == 0:
        logging.info("No documents to check - stopping")
        return

    logging.info("Retrieving tags from database for {} doc_ids...".format(len(doc_ids)))
    doc2tags = load_tags_for_doc_ids(doc_ids, collection)

    logging.info('Cleaning tuples...')
    i = 0
    len_tuples = len(tuples_cached)
    # tuples with just include tagged entities
    tuples_with_ent = []
    # don't include the same tuple twice for a single sentence
    already_included = set()
    # go trough all cached triples
    start_time = datetime.now()
    for openie_t in tuples_cached:
        if openie_t.doc_id not in doc2tags:
            continue
        doc_tags = doc2tags[openie_t.doc_id]
        # go trough all detected entities in the subject and object part of the open ie triple
        sub_ents, obj_ents = get_subject_and_object_entities(doc_tags, openie_t.subj, openie_t.obj)
        for s_txt, s_id, s_type in sub_ents:
            for o_txt, o_id, o_type in obj_ents:
                # check if tuple is already extracted for sentence
                key = (openie_t.doc_id, s_id, o_id, openie_t.pred, openie_t.sent)
                if key not in already_included:
                    t = PRED(openie_t.doc_id, openie_t.subj, openie_t.pred, openie_t.pred_lemma, openie_t.obj,
                             openie_t.conf, openie_t.sent, s_id, s_txt, s_type, o_id, o_txt, o_type)
                    tuples_with_ent.append(t)
                    already_included.add(key)

        print_progress_with_eta("Cleaning (entity based)", i, len_tuples, start_time)
        i += 1

    logging.info("{} facts remaining...".format(len(tuples_with_ent)))
    # now clean predicates
    tuples_cleaned = []
    len_tuples = len(tuples_with_ent)
    start_time = datetime.now()
    skipped_tuples = 0
    skipped_in_docs = set()
    passive_changed = 0
    for i, t in enumerate(tuples_with_ent):
        t_cleaned = _clean_tuple_predicate_based(t)
        if t_cleaned:
            # subject changed
            if t[1] != t_cleaned[1]:
                passive_changed += 1
            tuples_cleaned.append(t_cleaned)
        else:
            skipped_in_docs.add(t[0])
            skipped_tuples += 1
        print_progress_with_eta("Cleaning (predicates)", i, len_tuples, start_time)

    logging.info('Changed {} times passive voices (subj <-> obj swapped)'.format(passive_changed))
    logging.warning(
        '{} facts skipped (too long sentences) in {} documents'.format(skipped_tuples, len(skipped_in_docs)))
    logging.info('Cleaning finished...')

    insert_predications_into_db(tuples_cleaned, collection, extraction_type=OPENIE_EXTRACTION, version=OPENIE_VERSION)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help='OpenIE export file (exported by main.py / pipeline.py')
    parser.add_argument("-c", "--collection", required=True, help='document collection to which the ids belong')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    doc_ids, openie_tuples = read_stanford_openie_input(args.input)
    clean_open_ie(doc_ids, openie_tuples, args.collection)
    logging.info('finished')


if __name__ == "__main__":
    main()