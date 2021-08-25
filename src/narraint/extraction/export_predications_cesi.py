import argparse
import json
import logging
import random
from datetime import datetime

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication
from narrant.progress import print_progress_with_eta

# 80% are valid and 20% are valid
SPLIT_THRESHOLD_FOR_TEST_AND_VALID = 0.8


def load_predications_from_db():
    """
    Loads the facts from the database
    :return: a set o tuples
    """
    session = SessionExtended.get()
    query = session.query(Predication.document_id,
                          Predication.subject_str, Predication.subject_id, Predication.subject_str,
                          Predication.predicate,
                          Predication.object_str, Predication.sentence_id,
                          Predication.subject_type,
                          Predication.object_id, Predication.object_str, Predication.object_type)
    logging.info("loading predication tuples from db...")
    rows = session.execute(query)
    tuples = []
    for r in rows:
        tuples.append(r)
    logging.info('{} tuples load from db'.format(len(tuples)))
    return tuples


def aggregate_triples(tuples):
    """
    Aggregates the tuple for CESI
    :param tuples: database tuples
    :return: the aggregation
    """
    logging.info('aggregating of {} tuples by subject, predicate and object...'.format(len(tuples)))
    # go trough all cached triples
    aggregation = {}
    for pmid, subj, pred, obj, sent, sub_id, sub_ent, sub_type, obj_id, obj_ent, obj_type in tuples:
        key = frozenset((sub_id, pred, obj_id))
        t = (subj, pred, obj, sub_id, sub_ent, obj_id, obj_ent)
        if key not in aggregation:
            aggregation[key] = (t, [sent])
        else:
            aggregation[key][1].append(sent)
    return aggregation


def export_to_cesi(output):
    """
    Exports the database tuples in the CESI input format
    :param output: output filename
    :return: None
    """
    tuples_cached = load_predications_from_db()
    aggregation = aggregate_triples(tuples_cached)

    logging.info('exporting {} entries in CESI format to {}'.format(len(aggregation), output))
    start_time = datetime.now()
    size = len(aggregation)

    filename_test = '{}_test'.format(output)
    filename_valid = '{}_valid'.format(output)
    with open(output, 'w') as f:
        f_test = open(filename_test, 'w')
        f_valid = open(filename_valid, 'w')
        id_counter = 0
        for _, value in aggregation.items():
            t, sentences = value
            sub, pred, obj, sub_id, sub_ent, obj_id, obj_ent = t
            json_data = {'triple_norm': [sub.lower(), pred.lower(), obj.lower()],
                         'true_link': {'subject': sub_id, 'object': obj_id},
                         '_id': id_counter,
                         'triple': [sub, pred, obj],
                         'entity_linking': {'subject': sub, 'object': obj},
                         'kbp_info': [],
                         'src_sentences': sentences}

            json_str = '{}\n'.format(json.dumps(json_data))
            f.write(json_str)
            if random.random() > SPLIT_THRESHOLD_FOR_TEST_AND_VALID:
                f_valid.write(json_str)
            else:
                f_test.write(json_str)
            id_counter += 1
            print_progress_with_eta("exporting", id_counter, size, start_time)
        f_test.close()
        f_valid.close()
    logging.info('export finished')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help='export file (if CESI _test and _valid will also be created)')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logging.info('exporting in CESI format...')
    export_to_cesi(args.output)


if __name__ == "__main__":
    main()
