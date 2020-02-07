import argparse
import json
import logging
from datetime import datetime

from narraint.backend.database import Session
from narraint.backend.models import Predication
from narraint.progress import print_progress_with_eta


def load_tuples_from_db():
    session = Session.get()
    query = session.query(Predication.document_id, Predication.subject_openie, Predication.predicate,
                          Predication.object_openie, Predication.sentence,
                          Predication.subject_id, Predication.subject_str, Predication.subject_type,
                          Predication.object_id, Predication.object_str, Predication.object_type)
    logging.info("loading predication tuples from db...")
    rows = session.execute(query)
    tuples = []
    for r in rows:
        tuples.append(r)
    logging.info('{} tuples load from db'.format(len(tuples)))
    return tuples


def aggregate_triples(tuples):
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
    tuples_cached = load_tuples_from_db()
    aggregation = aggregate_triples(tuples_cached)

    logging.info('exporting {} entries in CESI format to {}'.format(len(aggregation), output))
    start_time = datetime.now()
    size = len(aggregation)
    with open(output, 'w') as f:
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

            json_str = json.dumps(json_data)
            f.write('{}\n'.format(json_str))
            id_counter += 1

            print_progress_with_eta("exporting", id_counter, size, start_time)

    logging.info('export finished')


def export_to_tsv(output):
    tuples = load_tuples_from_db()
    tuples_len = len(tuples)
    logging.info('exporting {} entries in TSV format to {}'.format(tuples_len, output))
    start_time = datetime.now()

    with open(output, 'w') as f:
        f.write('doc_id\tsubject_openie\tpredicate\tobject_openie\tsub_id\tsub_str\tsub_type\tobj_id\tobj_str'
                '\tobject_type\tsentence')
        for i, t in enumerate(tuples):
            doc_id, subj, pred, obj, sent, sub_id, sub_ent, sub_type, obj_id, obj_ent, obj_type = t
            f.write('\n{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(doc_id, subj, pred, obj, sub_id, sub_ent,
                                                                          sub_type, obj_id, obj_ent, obj_type, sent))

            print_progress_with_eta("exporting", i, tuples_len, start_time)

    logging.info('export finished')


def main():
    """

    Input: Directory with Pubtator files
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help='export file')
    parser.add_argument("-f", "--format",  action='store', choices=["CESI", "TSV"],
                        help='export format (supported: CESI | TSV)', required=True)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    if args.format == 'CESI':
        logging.info('exporting in CESI format...')
        export_to_cesi(args.output)
    elif args.format == 'TSV':
        logging.info("exporting in TSV format...")
        export_to_tsv(args.output)


if __name__ == "__main__":
    main()
