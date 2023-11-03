import logging
import argparse
import csv
import time
from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.frontend.ui.search_cache import SearchCache
from narraint.queryengine.engine import QueryEngine

COMMON_QUERIES = [
    '?X(Method) method Simvastatin',
    '?X(LabMethod) method Simvastatin',
    'Mass Spectrometry method Simvastatin'
]

DOCUMENT_COLLECTIONS = ['PubMed', 'LitCovid', "LongCovid", "ZBMed"]
NUM_QUERY_RUNS = 3


def execute_queries(cache, translation, result_writer):
    for q in COMMON_QUERIES:
        logging.info('Executing Query: {}'.format(q))
        graph_query, query_trans_string = translation.convert_query_text_to_fact_patterns(q)
        for i in range(NUM_QUERY_RUNS):
            start_time_with_caching = time.time()
            for collection in DOCUMENT_COLLECTIONS:
                try:
                    cached_results = cache.load_result_from_cache(collection, graph_query)
                except Exception:
                    logging.error('Cannot load query result from cache...')
                    results = QueryEngine.process_query_with_expansion(graph_query,
                                                                       document_collection_filter={collection})
                    try:
                        cache.add_result_to_cache(collection, graph_query, results)
                    except Exception:
                        logging.error('Cannot store query result to cache...')
            elapsed_time_with_caching = time.time() - start_time_with_caching
            logging.info('Query Execution Time with caching: {:.4f} seconds'.format(elapsed_time_with_caching))
            print("jojjojojoj")
            start_time_without_caching = time.time()
            for collection in DOCUMENT_COLLECTIONS:
                results = QueryEngine.process_query_with_expansion(graph_query,
                                                                   document_collection_filter={collection})
            elapsed_time_without_caching = time.time() - start_time_without_caching

            logging.info('Query Execution Time without caching: {:.4f} seconds'.format(elapsed_time_without_caching))
            result_writer.writerow([q, i, elapsed_time_with_caching, elapsed_time_without_caching])


def main():
    parser = argparse.ArgumentParser(description='Measure performance of the system.')
    parser.add_argument('result_file', help='Path to the result .tsv file')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    cache = SearchCache()
    translation = QueryTranslation()

    with open(args.result_file, 'w', newline='') as csvfile:
        result_writer = csv.writer(csvfile, delimiter='\t')
        result_writer.writerow(['Query', 'Iteration', 'Execution Time (seconds) with caching', 'Execution Time (seconds) without caching'])

        execute_queries(cache, translation, result_writer)


if __name__ == "__main__":
    main()