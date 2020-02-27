import os
import logging
import time

from narraint.config import TMP_DIR, UMLS_DATA, SEMMEDDB_CONFIG, LOG_DIR


class QueryLogger:

    def __init__(self, log_dir=LOG_DIR):
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)
        if not os.path.isdir(log_dir):
            raise Exception('no log dir avaiable {}'.format(log_dir))
        self.log_dir = log_dir
        self.log_header = 'timestamp\ttime needed\tcollection\tquery keywords\tfact patterns\tsql statement' \
                          '\tpmids result\n'

    def write_log(self, time_needed, collection, keywords, fact_patterns, sql_statement, pmids_results):
        log_file_name = os.path.join(self.log_dir, '{}-queries.log'.format(time.strftime("%Y-%m-%d")))
        timestr = time.strftime("%Y.%m.%d-%H:%M:%S")
        log_entry = '{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(timestr, time_needed, collection,
                                                          keywords, fact_patterns, sql_statement, pmids_results)

        if not os.path.isfile(log_file_name):
            logging.info('creating new log file: {}'.format(log_file_name))
            with open(log_file_name, 'w') as f:
                f.write(self.log_header)
                f.write(log_entry)
        else:
            logging.info('appending to log file: {}'.format(log_file_name))
            with open(log_file_name, 'a') as f:
                f.write(log_entry)

