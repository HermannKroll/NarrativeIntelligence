import os
from datetime import datetime

path = "/Users/hermannkroll/Downloads/logs_2023_01_30/NarrativeIntelligence/logs/queries/"


data = []
no_files = 0
for filename in os.listdir(path):
    try:
        with open(os.path.join(path, filename), 'r') as f:
            headers = f.readline().rstrip()
            header_list = headers.split('\t')
            for line in f.readlines():
                details = line.split('\t')
                details = [x.strip() for x in details]
                structure = {key: value for key, value in zip(header_list, details)}
                date = structure['timestamp'].split('-')[0]
                structure["date_object"] = datetime.strptime(date, '%Y.%m.%d').date()
                data.append(structure)
        no_files += 1
    except:
        print(f'ignoring: {filename}')

no_queries_without_query = 0
no_queries, no_queries_complex = 0, 0
for entry in data:
    if 'query string' not in entry:
        no_queries_without_query += 1
        continue

    no_queries += 1
    if '_AND_' in str(entry['query string']):
        no_queries_complex += 1

print(f'Analyzed {no_files} log files')
print(f'{no_queries_without_query} / {len(data)}')
print(f'Number of queries: {no_queries}')
print(f'Number of complex queries: {no_queries_complex}')
print(f'Ration: {no_queries_complex / no_queries}')