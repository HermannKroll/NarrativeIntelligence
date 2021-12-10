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
        self.log_dir_document_clicks = os.path.join(log_dir, "document_links")
        self.log_dir_api_calls = os.path.join(log_dir, "api_calls")
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
        if not os.path.isdir(self.log_dir_document_clicks):
            os.mkdir(self.log_dir_document_clicks)
        if not os.path.isdir(self.log_dir_api_calls):
            os.mkdir(self.log_dir_api_calls)

        self.log_header = 'timestamp\ttime needed\tcollection\tcache hit\thits\tquery string\tgraph query'
        self.prov_log_header = 'timestamp\ttime needed\tdocument collection\tdocument id\tprovenance ids'
        self.document_graph_log_header = 'timestamp\ttime needed\tdocument collection\tdocument id\t#facts'
        self.page_view_header = 'timestamp\tpage'
        self.rating_header = 'timestamp\tquery\tuser id\tprovenance ids'
        self.document_click_header = 'timestamp\tquery\tdocument collection\tdocument id\tlink'
        self.api_call_header = 'timestamp\tsuccess\troute\tcall'

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

    def write_provenance_log(self, time_needed, document_collection, document_id, provenance_ids):
        log_file_name = os.path.join(self.log_dir_prov, '{}-prov.log'.format(time.strftime("%Y-%m-%d")))
        timestr = time.strftime("%Y.%m.%d-%H:%M:%S")

        log_entry = f'\n{timestr}\t{time_needed}\t{document_collection}\t{document_id}\t{provenance_ids}'
        if not os.path.isfile(log_file_name):
            logging.debug('creating new provenance log file: {}'.format(log_file_name))
            with open(log_file_name, 'w') as f:
                f.write(self.prov_log_header)
                f.write(log_entry)
        else:
            logging.debug('appending to provenance log file: {}'.format(log_file_name))
            with open(log_file_name, 'a') as f:
                f.write(log_entry)

    def write_document_graph_log(self, time_needed, document_collection: str, document_id: int, number_facts: int):
        log_file_name = os.path.join(self.log_dir_document_graph,
                                     '{}-document_graphs.log'.format(time.strftime("%Y-%m-%d")))
        timestr = time.strftime("%Y.%m.%d-%H:%M:%S")

        log_entry = f'\n{timestr}\t{time_needed}\t{document_collection}\t{document_id}\t{number_facts}'
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

    def write_rating(self, query, user_id, provenance_ids):
        log_file_name = os.path.join(self.log_rating,
                                     '{}-ratings.log'.format(time.strftime("%Y-%m-%d")))
        timestr = time.strftime("%Y.%m.%d-%H:%M:%S")
        log_entry = f'\n{timestr}\t{query}\t{user_id}\t{provenance_ids}'
        if not os.path.isfile(log_file_name):
            logging.debug('creating new rating log file: {}'.format(log_file_name))
            with open(log_file_name, 'w') as f:
                f.write(self.rating_header)
                f.write(log_entry)
        else:
            logging.debug('appending to rating log file: {}'.format(log_file_name))
            with open(log_file_name, 'a') as f:
                f.write(log_entry)

    def write_document_link_clicked(self, query: str, document_collection: str, document_id: str, link: str):
        log_file_name = os.path.join(self.log_dir_document_clicks,
                                     '{}-documents_clicked.log'.format(time.strftime("%Y-%m-%d")))
        timestr = time.strftime("%Y.%m.%d-%H:%M:%S")
        log_entry = f'\n{timestr}\t{query}\t{document_collection}\t{document_id}\t{link}'
        if not os.path.isfile(log_file_name):
            logging.debug('creating new document click log file: {}'.format(log_file_name))
            with open(log_file_name, 'w') as f:
                f.write(self.document_click_header)
                f.write(log_entry)
        else:
            logging.debug('appending to document click log file: {}'.format(log_file_name))
            with open(log_file_name, 'a') as f:
                f.write(log_entry)

    def write_api_call(self, success: bool, route: str, call: str):
        try:
            log_file_name = os.path.join(self.log_dir_api_calls,
                                         '{}-api_calls.log'.format(time.strftime("%Y-%m-%d")))
            timestr = time.strftime("%Y.%m.%d-%H:%M:%S")
            log_entry = f'\n{timestr}\t{success}\t{route}\t{call}'
            if not os.path.isfile(log_file_name):
                logging.debug('creating new api call log file: {}'.format(log_file_name))
                with open(log_file_name, 'w') as f:
                    f.write(self.api_call_header)
                    f.write(log_entry)
            else:
                logging.debug('appending to api call log file: {}'.format(log_file_name))
                with open(log_file_name, 'a') as f:
                    f.write(log_entry)
        except IOError:
            logging.debug('Could not api call log file')
