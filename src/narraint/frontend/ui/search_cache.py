import hashlib
import logging
import os
import pickle

from narraint.config import CACHE_DIR
from narraint.queryengine.query import GraphQuery
from narraint.queryengine.result import QueryDocumentResult


class SearchCache:

    def __init__(self):
        if not os.path.isdir(CACHE_DIR):
            os.mkdir(CACHE_DIR)

    def convert_query_to_path(self, document_collection, graph_query: GraphQuery, aggregation_name: str = None):
        key = hashlib.md5(graph_query.get_unique_key().encode('utf-8')).hexdigest()
        if not aggregation_name:
            return os.path.join(CACHE_DIR, '{}_{}.pkl'.format(document_collection, key))
        else:
            return os.path.join(CACHE_DIR, '{}_{}_{}.pkl'.format(aggregation_name, document_collection, key))

    def add_result_to_cache(self, document_collection, graph_query: GraphQuery, results: [QueryDocumentResult],
                            aggregation_name: str = None):
        path = self.convert_query_to_path(document_collection, graph_query, aggregation_name=aggregation_name)
        logging.info(f'Write results to cache: {path}')
        with open(path, 'wb') as f:
            return pickle.dump(results, f)

    def load_result_from_cache(self, document_collection, graph_query: GraphQuery, aggregation_name: str = None):
        path = self.convert_query_to_path(document_collection, graph_query, aggregation_name=aggregation_name)
        if os.path.isfile(path):
            logging.info(f'Loading results from cache: {path}')
            with open(path, 'rb') as f:
                return pickle.load(f)
        return None
