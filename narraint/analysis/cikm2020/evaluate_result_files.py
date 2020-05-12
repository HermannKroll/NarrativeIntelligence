import glob
import logging
from itertools import islice


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    result_files = glob.glob('*.tsv')
    logging.info('{} results files found'.format(len(result_files)))
    for filename in result_files:
        with open(filename, 'rt') as f:
            avg_prec, avg_recall, counted_queries, query_len = 0.0, 0.0, 0, 0
            for line in islice(f, 1, None):
                comps = line.split('\t')
                sub_id, obj_id = comps[0], comps[1]
                pubmed_hits, graph_hits, precision, recall = int(comps[2]), int(comps[3]), float(comps[4]), float(comps[5])
                query_len += 1
                if pubmed_hits >= 3 and graph_hits >= 3:
                    counted_queries += 1
                    avg_prec += precision
                    avg_recall += recall
            avg_prec = avg_prec / counted_queries
            avg_recall = avg_recall / counted_queries
            logging.info('=' * 60)
            logging.info('File: {}'.format(filename))
            logging.info('Counted Queries: {} / {}'.format(counted_queries, query_len))
            logging.info('Mean Average Precision: {:1.3f}'.format(avg_prec))
            logging.info('Mean Average Recall: {:1.3f}'.format(avg_recall))
            logging.info('=' * 60)


if __name__ == "__main__":
    main()