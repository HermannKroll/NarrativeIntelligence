import argparse
import logging
import os

from narraint.queryengine.engine import QueryEngine


def build_entity_list(output):
    entities = QueryEngine.query_entities()
    with open(output, 'w') as f:
        for idx, (ent_id, ent_str) in enumerate(entities):
            if idx == 0:
                f.write('{}\t{}'.format(ent_str, ent_id))
            else:
                f.write('\n{}\t{}'.format(ent_str, ent_id))


def build_predicate_list(output):
    predicates = QueryEngine.query_predicates_cleaned()
    with open(output, 'w') as f:
        for idx, predicate in enumerate(predicates):
            if idx == 0:
                f.write('{}'.format(predicate))
            else:
                f.write('\n{}'.format(predicate))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help='output directory')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.DEBUG)
    ent_file = os.path.join(args.output, 'entities.txt')
    pred_file = os.path.join(args.output, 'predicates.txt')

    logging.info('Extracting database information in: {}'.format(args.output))
    logging.info('Retrieving entity information...')
    build_entity_list(ent_file)
    logging.info('Retrieving predicate information...')
    build_predicate_list(pred_file)
    logging.info('Finished')


if __name__ == "__main__":
    main()
