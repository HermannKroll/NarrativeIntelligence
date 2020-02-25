import argparse
import logging
from datetime import datetime
import re

import nltk
from nltk.corpus import wordnet

from sqlalchemy.dialects.postgresql import insert
from narraint.backend.models import Tag, Predication
from narraint.backend.database import Session
from narraint.openie.main import OPENIE_VERSION
from narraint.preprocessing.config import Config
from narraint.config import PREPROCESS_CONFIG
from narraint.progress import print_progress_with_eta

COMMIT_AFTER_INSERTS = 1000
MAX_SENTENCE_LENGTH = 3000

TOKENS_TO_IGNORE = set(['with', 'by', 'of', 'from', 'to', 'than', 'as', 'on', 'at', 'may', 'in', 'can', 'more', 'less',
                        'into', 'be', 'have', 'well', 'for'])


def get_subject_and_object_entities(doc_tags, sub, obj):
    # default not hit
    subs_included = []
    objs_included = []
    # compute lower case with empty spaces
    sub_text = ' {} '.format(sub.lower())
    obj_text = ' {} '.format(obj.lower())

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
    session = Session.get()
    # get all tags for the given doc_ids
    query = session.query(Tag.document_id, Tag.ent_id, Tag.ent_str, Tag.ent_type)
    query = query.filter(Tag.document_collection == collection)
    query = query.filter(Tag.document_id.in_(doc_ids))

    doc2tags = {}
    results = session.execute(query)
    counter = 0
    for row in results:
        ent_str = ' {} '.format(row[2]).lower()
        t = (row[1], ent_str, row[3])
        if row[0] not in doc2tags:
            doc2tags[row[0]] = [t]
        else:
            doc2tags[row[0]].append(t)
        counter += 1
    logging.info('{} tags load from db'.format(counter))
    return doc2tags


def insert_predications_into_db(tuples_cleaned, collection):
    session = Session.get()
    len_tuples = len(tuples_cleaned)
    logging.info('inserting {} tuples to database...'.format(len_tuples))
    start_time = datetime.now()
    for i, t in enumerate(tuples_cleaned):
        doc_id, subj, pred, pred_cleaned, p_pos_tags, obj, conf, sent, s_id, s_txt, s_type, o_id, o_txt, o_type = t
        # enforce inserting none
        if not pred_cleaned:
            pred_cleaned = None

        insert_pred = insert(Predication).values(
            document_id=doc_id,
            document_collection=collection,
            subject_openie=subj,
            subject_id=s_id,
            subject_str=s_txt,
            subject_type=s_type,
            predicate=pred,
            predicate_cleaned=pred_cleaned,
            object_openie=obj,
            object_id=o_id,
            object_str=o_txt,
            object_type=o_type,
            confidence=conf,
            sentence=sent,
            openie_version=OPENIE_VERSION
        ).on_conflict_do_nothing(
            index_elements=('document_id', 'document_collection', 'subject_id', 'predicate', 'object_id', 'sentence')
        )
        session.execute(insert_pred)
        if i % COMMIT_AFTER_INSERTS == 0:
            session.commit()

        print_progress_with_eta("inserting", i, len_tuples, start_time)

    logging.info('insert finished ({} facts inserted)'.format(len(tuples_cleaned)))
    session.commit()


def clean_tuple(t):
    doc_id, subj, pred, pred_lemma, obj, conf, sent, s_id, s_txt, s_type, o_id, o_txt, o_type = t
    fact_sentence = '{} {} {}.'.format(subj, pred, obj)
    fact_sentence_tokens = nltk.word_tokenize(fact_sentence)
    pos_tags = nltk.pos_tag(fact_sentence_tokens)

    # ignore tuples from too long sentences
    if len(sent) > MAX_SENTENCE_LENGTH:
        return None

    # ignore tuples containing just 'be' and 'have'
    if pred_lemma == 'be' or pred_lemma == 'have':
        return None

    pred_cleaned = ''
    # remove be and have if multiple tokens are included
    tokens = pred_lemma.split(' ')
    start_pred = len(subj.split(' '))
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

    # check for active and passive voice
    if ('be' in tokens and participe_past_detected) or ('caused by' in pred and participe_past_detected):
        # passive means we have to change the direction of the tuple
        t_sub, t_s_txt, t_s_id, t_s_type = subj, s_txt, s_id, s_type
        subj, s_txt, s_id, s_type = obj, o_txt, o_id, o_type
        obj, o_txt, o_id, o_type = t_sub, t_s_txt, t_s_id, t_s_type

    return doc_id, subj.strip(), pred.strip(), pred_cleaned.strip(), pos_tags, obj.strip(), conf, sent.strip(), s_id, \
           s_txt.strip(), s_type.strip(), o_id, o_txt.strip(), o_type.strip()


def clean_open_ie(input, collection):
    logging.info('beginning cleaning step...')
    doc_ids = set()
    tuples_cached = []
    # open the input open ie file
    with open(input, 'r') as f:
        # read all lines for a single doc
        for line in f:
            c = line.strip().split("\t")
            doc_id, subj, pred, pred_lemma, obj, conf, sent = c[0], c[1], c[2], c[3], c[4], c[5], c[6]
            doc_ids.add(int(doc_id))
            tuples_cached.append((int(doc_id), subj, pred, pred_lemma, obj, conf, sent))

    logging.info('{} OpenIE tuples read...'.format(len(tuples_cached)))

    if len(doc_ids) == 0:
        logging.info("no documents to check - stopping")
        return

    logging.info("retrieving tags from database for {} doc_ids...".format(len(doc_ids)))
    doc2tags = load_tags_for_doc_ids(doc_ids, collection)

    logging.info('cleaning tuples...')
    i = 0
    len_tuples = len(tuples_cached)
    # tuples with just include tagged entities
    tuples_with_ent = []
    # don't include the same tuple twice for a single sentence
    already_included = set()
    # go trough all cached triples
    start_time = datetime.now()
    for pmid, subj, pred, pred_lemma, obj, conf, sent in tuples_cached:
        if pmid not in doc2tags:
            continue
        doc_tags = doc2tags[pmid]
        # go trough all detected entities in the subject and object part of the open ie triple
        sub_ents, obj_ents = get_subject_and_object_entities(doc_tags, subj, obj)
        for s_txt, s_id, s_type in sub_ents:
            for o_txt, o_id, o_type in obj_ents:
                # check if tuple is already extracted for sentence
                key = frozenset((pmid, s_id, o_id, pred, sent))
                if key not in already_included:
                    t = (pmid, subj, pred, pred_lemma, obj, conf, sent, s_id, s_txt,
                         s_type, o_id, o_txt, o_type)
                    tuples_with_ent.append(t)
                    already_included.add(key)

        print_progress_with_eta("cleaning (entity based)", i, len_tuples, start_time)
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
        t_cleaned = clean_tuple(t)
        if t_cleaned:
            # subject changed
            if t[1] != t_cleaned[1]:
                passive_changed += 1
            tuples_cleaned.append(t_cleaned)
        else:
            skipped_in_docs.add(t[0])
            skipped_tuples += 1
        print_progress_with_eta("cleaning (predicates)", i, len_tuples, start_time)

    logging.info('changed {} times passive voices (subj <-> obj swapped)'.format(passive_changed))
    logging.warning(
        '{} facts skipped (too long sentences) in {} documents'.format(skipped_tuples, len(skipped_in_docs)))
    logging.info('cleaning finished...')

    insert_predications_into_db(tuples_cleaned, collection)


def main():
    """
    Input: Directory with Pubtator files
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help='OpenIE export file')
    parser.add_argument("-c", "--collection", required=True, help='collection to which the ids belong')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    # Create configuration wrapper
    conf = Config(PREPROCESS_CONFIG)
    clean_open_ie(args.input, args.collection)
    logging.info('finished')


if __name__ == "__main__":
    main()
