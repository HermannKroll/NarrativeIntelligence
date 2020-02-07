import argparse
import logging
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from narraint.backend.models import Tag, Predication
from narraint.backend.database import Session
from narraint.openie.main import OPENIE_VERSION
from narraint.preprocessing.config import Config
from narraint.config import PREPROCESS_CONFIG
from narraint.preprocessing.convertids import load_pmcids_to_pmid_index
from narraint.progress import print_progress_with_eta

COMMIT_AFTER_INSERTS = 1000


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
        doc_id, subj, pred, obj, sent, s_id, s_txt, s_type, o_id, o_txt, o_type = t

        insert_pred = insert(Predication).values(
            document_id=doc_id,
            document_collection=collection,
            subject_openie=subj,
            subject_id=s_id,
            subject_str=s_txt,
            subject_type=s_type,
            predicate=pred,
            object_openie=obj,
            object_id=o_id,
            object_str=o_txt,
            object_type=o_type,
            sentence=sent,
            openie_version=OPENIE_VERSION
        ).on_conflict_do_nothing(
            index_elements=('document_id', 'document_collection', 'subject_id', 'predicate', 'object_id', 'sentence')
        )
        session.execute(insert_pred)
        if i % COMMIT_AFTER_INSERTS == 0:
            session.commit()

        print_progress_with_eta("inserting", i, len_tuples, start_time)

    session.commit()


def clean_open_ie(input, output, collection, pmcid2pmid):
    logging.info('beginning cleaning step...')
    doc_ids = set()
    tuples_cached = []
    skipped_doc_ids = set()
    # open the input open ie file
    with open(input, 'r') as f:
        # read all lines for a single doc
        for line in f:
            c = line.strip().split("\t")
            pmcid, subj, pred, obj, sent = c[0], c[1], c[2], c[3], c[4]
            if pmcid in pmcid2pmid:
                pmid = pmcid2pmid[pmcid]
            else:
                skipped_doc_ids.add(pmcid)
                continue
            doc_ids.add(int(pmid))
            tuples_cached.append((int(pmid), subj, pred, obj, sent))

    if len(skipped_doc_ids) > 0:
        logging.warning('skipping the following document ids: {}'.format(skipped_doc_ids))
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
    tuples_cleaned = []
    # don't include the same tuple twice for a single sentence
    already_included = set()
    # go trough all cached triples
    start_time = datetime.now()
    for pmid, subj, pred, obj, sent in tuples_cached:
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
                    t = (pmid, subj, pred, obj, sent, s_id, s_txt, s_type, o_id, o_txt, o_type)
                    tuples_cleaned.append(t)
                    already_included.add(key)

        print_progress_with_eta("cleaning", i, len_tuples, start_time)
        i += 1

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

    pmcid2pmid = {}
    if args.collection == 'PMC':
        print('loading pmcid to pmid translation file...')
        pmcid2pmid = load_pmcids_to_pmid_index(conf.pmcid2pmid)

    clean_open_ie(args.input, args.output, args.collection, pmcid2pmid)


if __name__ == "__main__":
    main()
