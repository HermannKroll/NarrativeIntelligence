import logging
import datetime
from itertools import islice

files_to_analyse = ["performance_query_1.tsv", "performance_query_2.tsv", "performance_query_3.tsv",
                    "performance_query_variable_1.tsv", "performance_query_variable_2.tsv"]


def convert_time_to_milliseconds(time_str) -> int:
    """
    converts a timespan string to milliseconds as an integer
    :param time_str:
    :return:
    """
    ho_mi_sec, milliseconds_str = time_str.split('.')
    milliseconds = int(milliseconds_str[0:3])
    comps = ho_mi_sec.split(':')
    milliseconds += int(comps[2]) * 1000
    milliseconds += int(comps[1]) * 60 * 1000
    milliseconds += int(comps[0]) * 60 * 60 * 1000
    return milliseconds


def main():
    """
    Iterates over the performance evaluation files and computes average times 
    """
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    logging.info('Beginning analysis...')
    for file in files_to_analyse:
        logging.info('-' * 60)
        logging.info('Analysing: {}'.format(file))
        logging.info('-' * 60)
        with open(file, 'rt') as fp:
            count = 0
            avg_time_query = 0
            avg_result_size = 0
            for line in islice(fp, 1, None):
                time_query, result_size, _ = line.split('\t')
                count += 1
                time_query_datetime = convert_time_to_milliseconds(time_query)
                avg_time_query += float(time_query_datetime)
                avg_result_size += int(result_size)

            avg_time_query = avg_time_query / count
            avg_result_size = avg_result_size / count
            logging.info('Analysed {} queries'.format(count))
            logging.info('Average query time: {} ms'.format(avg_time_query))
            logging.info('Average result size: {}'.format(avg_result_size))
            system_throughput = 1000 / avg_time_query
            logging.info('System throughput: {} queries / s'.format(system_throughput))

        logging.info('-' * 60)
    logging.info('Finished')


if __name__ == "__main__":
    main()