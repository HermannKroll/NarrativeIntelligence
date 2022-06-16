import logging
import os
import time
from datetime import datetime

from narraint.config import LOG_DIR
from narraint.queryengine.query import GraphQuery


def write_entry(log_entry: str, log_file_name: str, log_header: str, log_type: str = ""):
    """
    Open or create log file (log_file_name) and append log entry. A time tag
    is added to the beginning of the entry beforehand.
    @param log_entry: action to be logged
    @param log_file_name: file in which the action is logged
    @param log_header: header which specifies the entry columns
    @param log_type: type shown in debug output
    """
    timestr = time.strftime("%Y.%m.%d-%H:%M:%S")
    log_entry = f"\n{timestr}\t{log_entry}"

    try:
        if not os.path.isfile(log_file_name):
            logging.debug(f'creating new {log_type} log file: {log_file_name}')
            with open(log_file_name, 'w') as f:
                f.write(log_header)
                f.write(log_entry)

        else:
            logging.debug(f'appending to {log_type} log file: {log_file_name}')
            with open(log_file_name, 'a') as f:
                f.write(log_entry)
    except IOError:
        logging.debug(f'Could not write entry into: {log_file_name}')


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
        self.log_subgroup_rating = os.path.join(log_dir, 'subgroup_ratings')
        self.log_dir_document_clicks = os.path.join(log_dir, "document_links")
        self.log_dir_api_calls = os.path.join(log_dir, "api_calls")
        if not os.path.isdir(log_dir):
            raise Exception(f'no provenance log dir available {log_dir}')
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
        if not os.path.isdir(self.log_subgroup_rating):
            os.mkdir(self.log_subgroup_rating)
        if not os.path.isdir(self.log_dir_document_clicks):
            os.mkdir(self.log_dir_document_clicks)
        if not os.path.isdir(self.log_dir_api_calls):
            os.mkdir(self.log_dir_api_calls)

        self.query_header = 'timestamp\ttime needed\tcollection\tcache hit\thits\tquery string\tgraph query'
        self.provenance_header = 'timestamp\ttime needed\tdocument collection\tdocument id\tprovenance ids'
        self.document_graph_header = 'timestamp\ttime needed\tdocument collection\tdocument id\t#facts'
        self.page_view_header = 'timestamp\tpage'
        self.rating_header = 'timestamp\tquery\tuser id\tprovenance ids'
        self.subgroup_rating_header = 'timestamp\tquery\tuser id\tvariable name\tentity name\tentity id\tentity type'
        self.document_click_header = 'timestamp\tquery\tdocument collection\tdocument id\tlink'
        self.api_call_header = 'timestamp\ttime needed\tsuccess\troute\tcall'

    def write_query_log(self, time_needed, collection, cache_hit: bool, hits_count: int, query_string: str,
                        graph_query: GraphQuery):
        log_file_name = os.path.join(self.log_dir_queries,
                                     f'{time.strftime("%Y-%m-%d")}-queries.log')

        log_entry = f'{time_needed}\t{collection}\t{cache_hit}\t{hits_count}\t{query_string}\t{str(graph_query)}'

        write_entry(log_entry, log_file_name, self.query_header, "query")

    def write_provenance_log(self, time_needed, document_collection, document_id, provenance_ids):
        log_file_name = os.path.join(self.log_dir_prov,
                                     f'{time.strftime("%Y-%m-%d")}-prov.log')

        log_entry = f'{time_needed}\t{document_collection}\t{document_id}\t{provenance_ids}'

        write_entry(log_entry, log_file_name, self.provenance_header, "provenance")

    def write_document_graph_log(self, time_needed, document_collection: str, document_id: int, number_facts: int):
        log_file_name = os.path.join(self.log_dir_document_graph,
                                     f'{time.strftime("%Y-%m-%d")}-document_graphs.log')

        log_entry = f'{time_needed}\t{document_collection}\t{document_id}\t{number_facts}'

        write_entry(log_entry, log_file_name, self.document_graph_header, "document graph")

    def write_page_view_log(self, page_name):
        log_file_name = os.path.join(self.log_dir_views,
                                     f'{time.strftime("%Y-%m-%d")}-views.log')
        log_entry = f'{page_name}'

        write_entry(log_entry, log_file_name, self.page_view_header, "page view")

    def write_rating(self, query, user_id, provenance_ids):
        log_file_name = os.path.join(self.log_rating,
                                     f'{time.strftime("%Y-%m-%d")}-ratings.log')

        log_entry = f'{query}\t{user_id}\t{provenance_ids}'

        write_entry(log_entry, log_file_name, self.rating_header, "rating")

    def write_subgroup_rating_log(self, query: str, user_id: str, variable_name: str, entity_name: str, entity_id: str, entity_type: str):
        log_file_name = os.path.join(self.log_subgroup_rating,
                                     f'{time.strftime("%Y-%m-%d")}-subgroup-ratings.log')

        log_entry = f'{query}\t{user_id}\t{variable_name}\t{entity_name}\t{entity_id}\t{entity_type}'

        write_entry(log_entry, log_file_name, self.subgroup_rating_header, "subgroup rating")

    def write_document_link_clicked(self, query: str, document_collection: str,
                                    document_id: str, link: str):
        log_file_name = os.path.join(self.log_dir_document_clicks,
                                     f'{time.strftime("%Y-%m-%d")}-documents_clicked.log')
        log_entry = f'{query}\t{document_collection}\t{document_id}\t{link}'

        write_entry(log_entry, log_file_name, self.document_click_header, "click")

    def write_api_call(self, success: bool, route: str, call: str,
                       time_needed=None):
        log_file_name = os.path.join(self.log_dir_api_calls,
                                     f'{time.strftime("%Y-%m-%d")}-api_calls.log')
        if not time_needed:
            now = datetime.now()
            time_needed = now - now

        log_entry = f'{time_needed}\t{success}\t{route}\t{call}'
        write_entry(log_entry, log_file_name, self.api_call_header, "api call")
