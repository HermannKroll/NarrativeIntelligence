import os
from collections import defaultdict
from datetime import datetime

from narraint.config import LOG_DIR

narrative_path = os.path.join(LOG_DIR + "/queries")
overview_path = os.path.join(LOG_DIR + "/drug_ov_search")


def get_date_of_today():
    return datetime.now().date();


def get_json_of_log(path):
    data = []
    for filename in os.listdir(path):
        try:
            with open(os.path.join(path, filename), 'r') as f:
                headers = f.readline().rstrip()
                header_list = headers.split('\t')
                for line in f.readlines():
                    line = line.lower()
                    details = line.split('\t')
                    details = [x.strip() for x in details]
                    structure = {key: value for key, value in zip(header_list, details)}
                    date = structure['timestamp'].split('-')[0]
                    structure["date_object"] = datetime.strptime(date, '%Y.%m.%d').date()
                    data.append(structure)
        except:
            pass

    return data


def get_list_of_parameter(json_object, parameter):
    today = datetime.now().date()
    parameter_list = []
    for i in json_object:
        if i.__contains__(parameter) and not i[parameter] in parameter_list:
            parameter_list.append(i[parameter])
    parameter_list = sorted(parameter_list)
    # print(parameter_list)
    return parameter_list


def get_most_searched_parameter(top_k, json_object_narrative, json_object_overview):
    result_queries = get_most_searched_parameter_per_time(top_k, json_object_narrative, "query string")
    result_overview = get_most_searched_parameter_per_time(top_k, json_object_overview, "drug")

    return result_queries, result_overview


def get_most_searched_parameter_per_time(top_k, json_object, parameter):
    today = datetime.now().date()
    parameter_list = list(set(get_list_of_parameter(json_object, parameter)))
    counter_per_parameter = {"t": {}, "tw": {}, "tm": {}, "ty": {}, "a": {}}
    for p in parameter_list:
        counter_per_parameter["t"][p] = 0
        counter_per_parameter["tw"][p] = 0
        counter_per_parameter["tm"][p] = 0
        counter_per_parameter["ty"][p] = 0
        counter_per_parameter["a"][p] = 0
    for i in json_object:
        if i.__contains__(parameter):
            date_object = i["date_object"]
            parameter_value = i[parameter]
            if date_object == today:
                counter_per_parameter["t"][parameter_value] += 1
            # Returns the calendar week
            if date_object.isocalendar()[1] == today.isocalendar()[1] and date_object.year == today.year:
                counter_per_parameter["tw"][parameter_value] += 1
            if date_object.month == today.month and date_object.year == today.year:
                counter_per_parameter["tm"][parameter_value] += 1
            if date_object.year == today.year:
                counter_per_parameter["ty"][parameter_value] += 1
            counter_per_parameter["a"][parameter_value] += 1

    counter_per_parameter_sorted = {}
    for date_agg, values in counter_per_parameter.items():
        value_list = list([(k, v) for k, v in values.items() if v > 0])
        value_list.sort(key=lambda x: x[1], reverse=True)
        counter_per_parameter_sorted[date_agg] = {q: count for q, count in value_list[:top_k]}

    return counter_per_parameter_sorted


def get_amount_of_occurrences(json_object):
    today = datetime.now().date()
    counter = {"t": 0, "tw": 0, "tm": 0, "lm": 0, "ty": 0, "ly": 0}
    for i in json_object:
        date_object = i["date_object"]
        if date_object.year == today.year - 1:
            counter["ly"] += 1
        elif date_object.year == today.year:
            counter["ty"] += 1
            if date_object.month == today.month - 1:
                counter["lm"] += 1
            elif date_object.month == today.month:
                counter["tm"] += 1
            # Calendar week can range over a month
            # Returns the calendar week
            if date_object.isocalendar()[1] == today.isocalendar()[1]:
                counter["tw"] += 1
                if date_object == today:
                    counter["t"] += 1
    return counter


def get_all_amounts_of_occurrences(narrative_json, overview_json):
    amounts_narrative = get_amount_of_occurrences(narrative_json)
    amounts_overview = get_amount_of_occurrences(overview_json)
    return amounts_narrative, amounts_overview


def get_graph_input_per_time(json_object, time_deltas):
    today = datetime.now().date()

    count_per_day_and_time = {}
    for time_delta in time_deltas:
        count_per_day_and_time[time_delta] = defaultdict(int)

    for i in json_object:
        date_object = i["date_object"]
        for time_delta in time_deltas:
            for j in range(0, time_delta + 1):
                if j == (today - date_object).days:
                    count_per_day_and_time[time_delta][j] += 1

    return count_per_day_and_time


def get_graph_input(json_object_narrative, json_object_overview):
    result_narrative = get_graph_input_per_time(json_object_narrative, [7, 31, 182, 365])

    result_overview = get_graph_input_per_time(json_object_overview, [7, 31, 182, 365])
    return result_narrative, result_overview


def create_dictionary_of_logs():
    narrative_json = get_json_of_log(narrative_path)
    overview_json = get_json_of_log(overview_path)
    result = dict()
    result_narrative = dict()
    result_overview = dict()
    result_narrative['topQueries'], result_overview['topQueries'] = get_most_searched_parameter(100,
                                                                                                narrative_json,
                                                                                                overview_json)
    result_narrative['amountQueries'], result_overview['amountQueries'] = get_all_amounts_of_occurrences(narrative_json,
                                                                                                         overview_json)
    result_narrative['graphInput'], result_overview['graphInput'] = get_graph_input(narrative_json, overview_json)
    result['narrative'] = result_narrative
    result['overview'] = result_overview
    result['today'] = get_date_of_today()
    return result


def main():
    # print(get_json_of_log(narrative_path))
    # query_json = get_json_of_log(narrative_path)
    # print(get_amount_of_queries(query_json, "t"))
    # top_queries = get_most_searched_queries(5, query_json, "query string")
    # print(top_queries)
    # print('Amount of queries performed in the last week: {}'.format(get_amount_of_queries(query_json, "w")))
    # print('Amount of queries performed in the last month: {}'.format(get_amount_of_queries(query_json, "m")))
    # print(create_dictionary_of_logs())
    # print(get_graph_input(query_json))
    get_json_of_log(overview_path)


if __name__ == "__main__":
    main()
