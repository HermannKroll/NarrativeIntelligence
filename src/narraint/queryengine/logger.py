import logging
import os
import time

from narraint.config import LOG_DIR
from narraint.queryengine.query import GraphQuery


class QueryLogger:

    def __init__(self, log_dir=LOG_DIR):
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)
        if not os.path.isdir(log_dir):
            raise Exception('no log dir available {}'.format(log_dir))
        self.log_dir = log_dir
        self.log_dir_queries = os.path.join(log_dir, 'queries')
        self.log_dir_prov = os.path.join(log_dir, 'provenance')
        self.log_dir_document_graph = os.path.join(log_dir, 'document_graphs')
        self.log_dir_views = os.path.join(log_dir, 'views')
        self.log_rating = os.path.join(log_dir, 'ratings')
        if not os.path.isdir(log_dir):
            raise Exception('no provenance log dir available {}'.format(log_dir))
        if not os.path.isdir(self.log_dir_queries):
            os.mkdir(self.log_dir_queries)
        if not os.path.isdir(self.log_dir_prov):
            os.mkdir(self.log_dir_prov)
        if not os.path.isdir(self.log_dir_document_graph):
            os.mkdir(self.log_dir_document_graph)
        if not os.path.isdir(self.log_dir_views):
            os.mkdir(self.log_dir_views)
        if not os.path.isdir(self.log_rating):
            os.mkdir(self.log_rating)

        self.log_header = 'timestamp\ttime needed\tcollection\tcache hit\thits\tquery string\tgraph query'
        self.prov_log_header = 'timestamp\ttime needed\tprovenance ids'
        self.document_graph_log_header = 'timestamp\ttime needed\tdocument_id\t#facts'
        self.page_view_header = 'timestamp\tpage'
        self.rating_header = 'timestamp\tuser id\tprovenance ids'

    def write_query_log(self, time_needed, collection, cache_hit: bool, hits_count: int, query_string: str,
                        graph_query: GraphQuery):
        log_file_name = os.path.join(self.log_dir_queries, '{}-queries.log'.format(time.strftime("%Y-%m-%d")))
        timestr = time.strftime("%Y.%m.%d-%H:%M:%S")
        log_entry = '\n{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(timestr, time_needed, collection, cache_hit, hits_count,
                                                          query_string, str(graph_query))

        if not os.path.isfile(log_file_name):
            logging.debug('creating new log file: {}'.format(log_file_name))
            with open(log_file_name, 'w') as f:
                f.write(self.log_header)
                f.write(log_entry)
        else:
            logging.debug('appending to log file: {}'.format(log_file_name))
            with open(log_file_name, 'a') as f:
                f.write(log_entry)

    def write_provenance_log(self, time_needed, provenance_ids):
        log_file_name = os.path.join(self.log_dir_prov, '{}-prov.log'.format(time.strftime("%Y-%m-%d")))
        timestr = time.strftime("%Y.%m.%d-%H:%M:%S")

        log_entry = f'\n{timestr}\t{time_needed}\t{provenance_ids}'
        if not os.path.isfile(log_file_name):
            logging.debug('creating new provenance log file: {}'.format(log_file_name))
            with open(log_file_name, 'w') as f:
                f.write(self.prov_log_header)
                f.write(log_entry)
        else:
            logging.debug('appending to provenance log file: {}'.format(log_file_name))
            with open(log_file_name, 'a') as f:
                f.write(log_entry)

    def write_document_graph_log(self, time_needed, document_id: int, number_facts: int):
        log_file_name = os.path.join(self.log_dir_document_graph,
                                     '{}-document_graphs.log'.format(time.strftime("%Y-%m-%d")))
        timestr = time.strftime("%Y.%m.%d-%H:%M:%S")

        log_entry = f'\n{timestr}\t{time_needed}\t{document_id}\t{number_facts}'
        if not os.path.isfile(log_file_name):
            logging.debug('creating new document graph log file: {}'.format(log_file_name))
            with open(log_file_name, 'w') as f:
                f.write(self.document_graph_log_header)
                f.write(log_entry)
        else:
            logging.debug('appending to document graph log file: {}'.format(log_file_name))
            with open(log_file_name, 'a') as f:
                f.write(log_entry)

    def write_page_view_log(self, page_name):
        log_file_name = os.path.join(self.log_dir_views,
                                     '{}-views.log'.format(time.strftime("%Y-%m-%d")))
        timestr = time.strftime("%Y.%m.%d-%H:%M:%S")

        log_entry = f'\n{timestr}\t{page_name}'
        if not os.path.isfile(log_file_name):
            logging.debug('creating new page view log file: {}'.format(log_file_name))
            with open(log_file_name, 'w') as f:
                f.write(self.page_view_header)
                f.write(log_entry)
        else:
            logging.debug('appending to page view log file: {}'.format(log_file_name))
            with open(log_file_name, 'a') as f:
                f.write(log_entry)

    def write_rating(self, user_id, provenance_ids):
        log_file_name = os.path.join(self.log_rating,
                                     '{}-ratings.log'.format(time.strftime("%Y-%m-%d")))
        timestr = time.strftime("%Y.%m.%d-%H:%M:%S")
        log_entry = f'\n{timestr}\t{user_id}\t{provenance_ids}'
        if not os.path.isfile(log_file_name):
            logging.debug('creating new rating log file: {}'.format(log_file_name))
            with open(log_file_name, 'w') as f:
                f.write(self.rating_header)
                f.write(log_entry)
        else:
            logging.debug('appending to rating log file: {}'.format(log_file_name))
            with open(log_file_name, 'a') as f:
                f.write(log_entry)
