import json
import os
from datetime import datetime, timedelta
import pandas as pd
from narraint.config import LOG_DIR

narrative_path = os.path.join(LOG_DIR + "/queries")
overview_path = os.path.join(LOG_DIR + "/drug_ov_search")


def get_date_of_today():
    return datetime.now().date();


def get_json_of_log(path):
    data = []
    for filename in os.listdir(path):
        with open(os.path.join(path, filename), 'r') as f:
            headers = f.readline().rstrip()
            header_list = headers.split('\t')
            for line in f.readlines():
                details = line.split('\t')
                details = [x.strip() for x in details]
                structure = {key: value for key, value in zip(header_list, details)}
                data.append(structure)
    data_json = json.dumps(data, indent=4)
    #print(data_json)
    json_object = json.loads(data_json)
    return json_object


def get_list_of_parameter(json_object, parameter):
    today = datetime.now().date()
    parameter_list = []
    for i in json_object:
        if i.__contains__(parameter) and not i[parameter] in parameter_list:
            parameter_list.append(i[parameter])
    parameter_list = sorted(parameter_list)
    #print(parameter_list)
    return parameter_list


def get_most_searched_parameter(amount, json_object_narrative, json_object_overview):
    result_queries = dict()
    result_queries["t"] = get_most_searched_parameter_per_time(amount, json_object_narrative, "query string", "t")
    result_queries["tw"] = get_most_searched_parameter_per_time(amount, json_object_narrative, "query string", "tw")
    result_queries["tm"] = get_most_searched_parameter_per_time(amount, json_object_narrative, "query string", "tm")
    result_queries["ty"] = get_most_searched_parameter_per_time(amount, json_object_narrative, "query string", "ty")
    result_queries["a"] = get_most_searched_parameter_per_time(amount, json_object_narrative, "query string", "a")

    result_overview = dict()
    result_overview["t"] = get_most_searched_parameter_per_time(amount, json_object_overview, "drug", "t")
    result_overview["tw"] = get_most_searched_parameter_per_time(amount, json_object_overview, "drug", "tw")
    result_overview["tm"] = get_most_searched_parameter_per_time(amount, json_object_overview, "drug", "tm")
    result_overview["ty"] = get_most_searched_parameter_per_time(amount, json_object_overview, "drug", "ty")
    result_overview["a"] = get_most_searched_parameter_per_time(amount, json_object_overview, "drug", "a")
    return result_queries, result_overview


def get_most_searched_parameter_per_time(amount, json_object, parameter, time):
    today = datetime.now().date()
    parameter_list = get_list_of_parameter(json_object, parameter)
    amount_list = []
    for p in parameter_list:
        amount_list.append(0)
    for i in json_object:
        if i.__contains__(parameter):
            if i.__contains__('timestamp') and i['timestamp'] != '':
                date = i['timestamp'].split('-')[0]
                date_object = datetime.strptime(date, '%Y.%m.%d').date()
                if time == "t":
                    if date_object == today:
                        amount_list[parameter_list.index(i[parameter])] += 1
                elif time == "tw":
                    if date_object > today - timedelta(days=today.weekday()):
                        amount_list[parameter_list.index(i[parameter])] += 1
                elif time == "tm":
                    if date_object.month == today.month and date_object.year == today.year:
                        amount_list[parameter_list.index(i[parameter])] += 1
                elif time == "ty":
                    if date_object.year == today.year:
                        amount_list[parameter_list.index(i[parameter])] += 1
                elif time == "a":
                    amount_list[parameter_list.index(i[parameter])] += 1
    match_list = zip(amount_list, parameter_list)
    match_list = sorted(match_list)
    match_list.reverse()
    # print(match_list)
    top_list = dict()
    list_range = 0
    if len(match_list) < amount:
        list_range = len(match_list)
    else:
        list_range = amount
    for j in range(list_range):
        top_list[match_list[j][1]] = match_list[j][0]
    # print(top_list)
    return top_list


def get_amount_of_occurrences(json_object, time):
    today = datetime.now().date()
    counter = 0
    for i in json_object:
        if i.__contains__('timestamp') and i['timestamp'] != '':
            date = i['timestamp'].split('-')[0]
            date_object = datetime.strptime(date, '%Y.%m.%d').date()
            if time == "t":
                if date_object == today:
                    counter += 1
            elif time == "tw":
                if date_object > today - timedelta(days=today.weekday()):
                    counter += 1
            elif time == "tm":
                if date_object.month == today.month and date_object.year == today.year:
                    counter += 1
            elif time == "lm":
                if date_object.month == today.month - 1 and date_object.year == today.year:
                    counter += 1
            elif time == "ty":
                if date_object.year == today.year:
                    counter += 1
            elif time == "ly":
                if date_object.year == today.year - 1:
                    counter += 1
    return counter


def get_all_amounts_of_occurrences(narrative_json, overview_json):
    amounts_narrative = dict()
    amounts_narrative["t"] = get_amount_of_occurrences(narrative_json, "t")
    amounts_narrative["tw"] = get_amount_of_occurrences(narrative_json, "tw")
    amounts_narrative["tm"] = get_amount_of_occurrences(narrative_json, "tm")
    amounts_narrative["lm"] = get_amount_of_occurrences(narrative_json, "lm")
    amounts_narrative["ty"] = get_amount_of_occurrences(narrative_json, "ty")
    amounts_narrative["ly"] = get_amount_of_occurrences(narrative_json, "ly")

    amounts_overview = dict()
    amounts_overview["t"] = get_amount_of_occurrences(overview_json, "t")
    amounts_overview["tw"] = get_amount_of_occurrences(overview_json, "tw")
    amounts_overview["tm"] = get_amount_of_occurrences(overview_json, "tm")
    amounts_overview["lm"] = get_amount_of_occurrences(overview_json, "lm")
    amounts_overview["ty"] = get_amount_of_occurrences(overview_json, "ty")
    amounts_overview["ly"] = get_amount_of_occurrences(overview_json, "ly")
    return amounts_narrative, amounts_overview


def get_graph_input_per_time(json_object, time):
    today = datetime.now().date()
    time_limit = today - timedelta(days=time)
    amount_per_day = dict()
    start = time
    for t in range(time + 1):
        counter = 0
        for i in json_object:
            if i.__contains__('timestamp') and i['timestamp'] != '':
                date = i['timestamp'].split('-')[0]
                date_object = datetime.strptime(date, '%Y.%m.%d').date()
                if date_object == time_limit + timedelta(days=t):
                    counter += 1
        amount_per_day[start] = counter
        start -= 1
    return amount_per_day


def get_graph_input(json_object_narrative, json_object_overview):
    result_narrative = dict()
    result_narrative["7"] = get_graph_input_per_time(json_object_narrative, 7)
    result_narrative["31"] = get_graph_input_per_time(json_object_narrative, 31)
    result_narrative["182"] = get_graph_input_per_time(json_object_narrative, 182)
    result_narrative["365"] = get_graph_input_per_time(json_object_narrative, 365)

    result_overview = dict()
    result_overview["7"] = get_graph_input_per_time(json_object_overview, 7)
    result_overview["31"] = get_graph_input_per_time(json_object_overview, 31)
    result_overview["182"] = get_graph_input_per_time(json_object_overview, 182)
    result_overview["365"] = get_graph_input_per_time(json_object_overview, 365)
    return result_narrative, result_overview


def create_dictionary_of_logs():
    narrative_json = get_json_of_log(narrative_path)
    overview_json = get_json_of_log(overview_path)
    result = dict()
    result_narrative = dict()
    result_overview = dict()
    result_narrative['topTenQueries'], result_overview['topTenQueries'] = get_most_searched_parameter(100, narrative_json, overview_json)
    result_narrative['amountQueries'], result_overview['amountQueries'] = get_all_amounts_of_occurrences(narrative_json, overview_json)
    result_narrative['graphInput'], result_overview['graphInput'] = get_graph_input(narrative_json, overview_json)
    result['narrative'] = result_narrative
    result['overview'] = result_overview
    result['today'] = get_date_of_today()
    return result


def main():
    #print(get_json_of_log(narrative_path))
    #query_json = get_json_of_log(narrative_path)
    #print(get_amount_of_queries(query_json, "t"))
    # top_queries = get_most_searched_queries(5, query_json, "query string")
    # print(top_queries)
    # print('Amount of queries performed in the last week: {}'.format(get_amount_of_queries(query_json, "w")))
    # print('Amount of queries performed in the last month: {}'.format(get_amount_of_queries(query_json, "m")))
    #print(create_dictionary_of_logs())
   # print(get_graph_input(query_json))
   get_json_of_log(overview_path)


if __name__ == "__main__":
    main()
