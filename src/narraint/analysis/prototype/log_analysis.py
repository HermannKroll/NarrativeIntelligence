import glob
import itertools
import logging
from argparse import ArgumentParser
from collections import defaultdict


def analyze_query_logs(log_dir: str, output_file: str):
    all_logs = glob.glob(f'{log_dir}/**/*.log', recursive=True)

    count_queries = defaultdict(lambda: int(0))
    query_count = 0
    for log in all_logs:
        with open(log, 'rt') as f:
            try:
                for line in itertools.islice(f, 1, None):
                    timestamp, time_needed, collection, cache_hit, hits, query, trans_query = line.split('\t')

                    query_count += 1
                    count_queries[query] += 1
            except ValueError:
                pass # old log format
    print(count_queries)

    count_queries_sorted = sorted([(q, c) for q, c in count_queries.items()], key=lambda x: x[1], reverse=True)

    with open(output_file, 'wt') as f:
        f.write('='*60+'\n')
        f.write(' '*25 + 'Log Summary\n')
        f.write(f'  Queries         : {query_count}\n')
        f.write(f'  Distinct Queries: {len(count_queries)}\n')
        f.write('='*60+'\n')
        f.write('Most frequent queries:\n')
        f.write('-'*60+'\n')
        for query, count in count_queries_sorted:
            f.write(f'{count}\t{query}\n')


def main():
    logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO)

    parser = ArgumentParser(description="Log Analysis Tool (for Narrative Service Logs)")
    parser.add_argument("input", help="Input Directory of Logs", metavar="DIR")
    parser.add_argument("output", help="Output summary file", metavar="FILE")
    args = parser.parse_args()

    analyze_query_logs(args.input, args.output)



if __name__ == "__main__":
    main()
