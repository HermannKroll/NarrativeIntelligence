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
            raise Exception('no log dir avaiable {}'.format(log_dir))
        self.log_dir = log_dir
        self.log_header = 'timestamp\ttime needed\tcollection\tcache hit\thits\tquery string\tgraph query\n'

    def write_log(self, time_needed, collection, cache_hit: bool, hits_count: int, query_string: str,
                  graph_query: GraphQuery):
        log_file_name = os.path.join(self.log_dir, '{}-queries.log'.format(time.strftime("%Y-%m-%d")))
        timestr = time.strftime("%Y.%m.%d-%H:%M:%S")
        log_entry = '{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(timestr, time_needed, collection, cache_hit, hits_count,
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
