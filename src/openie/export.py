import argparse
import json
import logging

SQL_HEADER = "CREATE TABLE IF NOT EXISTS PREDICATION_OPENIE \
                 (predication_id INTEGER PRIMARY KEY, \
                  pmid INTEGER, \
                  subject_cui VARCHAR, \
                  subject_name VARCHAR, \
                  subject_semtype VARCHAR, \
                  object_cui VARCHAR, \
                  object_name VARCHAR, \
                  object_semtype VARCHAR, \
                  predication VARCHAR, \
                  sentence VARCHAR );\n"
SQL_INSERT_HEADER = 'INSERT INTO PREDICATION_OPENIE VALUES \n';

def read_input_tuples(input, logger):
    # open the input open ie file
    # read all lines for a single doc
    tuples_cached = []
    logger.info('reading input file {}'.format(input))
    with open(input, 'r') as f:
        for line in f:
            components = line.replace('\n', '').split("\t")
            pmid = components[0]
            subj = components[1]
            pred = components[2]
            obj = components[3]
            sent = components[4]
            sub_id = components[5]
            sub_ent = components[6]
            sub_type = components[7]
            obj_id = components[8]
            obj_ent = components[9]
            obj_type = components[10]
            tuples_cached.append((pmid, subj, pred, obj, sent, sub_id, sub_ent, sub_type, obj_id, obj_ent, obj_type))
    return tuples_cached


def aggregate_triples(tuples, logger):
    logger.info('aggregatign of {} tuples by subject, predicate and object...'.format(len(tuples)))
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


def export_to_cesi(input, output, logger):
    tuples_cached = read_input_tuples(input, logger)
    aggregation = aggregate_triples(tuples_cached, logger)

    logger.info('exporting {} entries in CESI format to {}'.format(len(aggregation), output))
    with open(output, 'w') as f:
        id_counter = 0
        for _, value in aggregation.items():
            t, sentences = value
            sub, pred, obj, sub_id, sub_ent, obj_id, obj_ent = t
            # Todo: lemmatize predicate
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
    logger.info('export finished')


def export_to_sql(input, output, logger):
    tuples = read_input_tuples(input, logger)

    logger.info('exporting {} entries in SQL format to {}'.format(len(tuples), output))
    with open(output, 'w') as f:
        f.write(SQL_HEADER)
        f.write(SQL_INSERT_HEADER)
        id_counter = 0
        for pmid, subj, pred, obj, sent, sub_id, sub_ent, sub_type, obj_id, obj_ent, obj_type in tuples:
            sub_ent_t = sub_ent.replace('\'', '\'\'')
            obj_ent_t = obj_ent.replace('\'', '\'\'')
            pred_t = pred.replace('\'', '\'\'')
            sent_t = sent.replace('\'', '\'\'')
            # ('1', '1', 'D01', 'Simvastatin', 'Drug', 'D02', 'CYP', 'Gene', 'metabolised_by'),
            insert_into = "({}, {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(id_counter, pmid,
                                                                          sub_id, sub_ent_t, sub_type,
                                                                          obj_id, obj_ent_t, obj_type,
                                                                          pred_t, sent_t)
            if id_counter != len(tuples)-1:
                insert_into += ',\n'

            f.write(insert_into)

            id_counter += 1
        f.write(';')

    logger.info('export finished')


def main():
    """

    Input: Directory with Pubtator files
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help='OpenIE export file to read')
    parser.add_argument("output", help='export file')
    parser.add_argument("-f", "--format", dest='format', action='store', help='export format (supported: CESI | SQL)',
                        required=True)
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)

    logger = logging.getLogger(__name__)

    ex_format = args.format
    if ex_format == 'CESI':
        logging.info('exporting in CESI format...')
        export_to_cesi(args.input, args.output, logger)
    if ex_format == 'SQL':
        logging.info("exporting to SQL statements...")
        export_to_sql(args.input, args.output, logger)


if __name__ == "__main__":
    main()
