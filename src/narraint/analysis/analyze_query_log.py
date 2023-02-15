import os
from datetime import datetime


def get_log_files(path):
    no_files = 0
    data = []
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
    return data, no_files


log_path = "/home/kroll/NarrativeIntelligence/data/logs_2023_02_15/NarrativeIntelligence/logs/"
path_narrative_service = os.path.join(log_path, "queries")
path_overviews = os.path.join(log_path, "drug_ov_search")

narrative_data, no_files = get_log_files(path_narrative_service)

year2count = {}

no_queries_without_query = 0
no_queries, no_queries_complex = 0, 0
for entry in narrative_data:
    date_object = entry["date_object"]
    if date_object.year in year2count:
        year2count[date_object.year] += 1
    else:
        year2count[date_object.year] = 1
    if 'query string' not in entry:
        no_queries_without_query += 1
        continue

    no_queries += 1
    if '_AND_' in str(entry['query string']):
        no_queries_complex += 1

print(f'Analyzed {no_files} log files')
print(f'{no_queries_without_query} / {len(narrative_data)}')
print(f'Number of queries: {no_queries}')
print(f'Number of complex queries: {no_queries_complex}')
print(f'Ration: {no_queries_complex / no_queries}')

print("\nQueries by Year (Narrative Service):")
print(sorted([(k, v) for k, v in year2count.items()], key=lambda x: x[0]))

overview_data, no_files = get_log_files(path_overviews)
year2count = {}
for entry in overview_data:
    date_object = entry["date_object"]
    if date_object.year in year2count:
        year2count[date_object.year] += 1
    else:
        year2count[date_object.year] = 1

print("\nQueries by Year (Drug Overviews):")
print(sorted([(k, v) for k, v in year2count.items()], key=lambda x: x[0]))
