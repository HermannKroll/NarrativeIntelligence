import logging

from flask import Flask, url_for, request, abort

from narraint.analysis.querytranslation.data_graph import DataGraph, Query, QueryVariable
from narraint.analysis.querytranslation.entityresolverjcdl import EntityResolverJCDL
from narraint.analysis.querytranslation.ranker import MostSpecificQueryWithResults, AssociatedRankerWithQueryResults, \
    MostSupportedQuery, QueryRanker
from narraint.analysis.querytranslation.translation import SchemaGraph, QueryTranslationToGraph

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.INFO)

data_graph = DataGraph()
schema_graph = SchemaGraph()
translation = QueryTranslationToGraph(data_graph=data_graph, schema_graph=schema_graph)
entity_resolver = EntityResolverJCDL.instance()

ranker_strategies: [QueryRanker] = [MostSpecificQueryWithResults, AssociatedRankerWithQueryResults, MostSupportedQuery]

app = Flask(__name__)


def entity_to_str(entity):
    if isinstance(entity, QueryVariable):
        return str(entity.entity_type).capitalize()
    else:
        name = entity_resolver.get_name_for_var_ent_id(entity)
        if name[0].islower():
            name = name.capitalize()
        if '//' in name:
            name = name.split('//')[1]
        return name


def query_to_json(q: Query):
    result = {"terms": [t for t in sorted(q.terms)],
              "statements": []}
    entities_in_statements = set()
    for s, p, o in q.statements:
        entities_in_statements.add(s)
        entities_in_statements.add(o)
        result["statements"].append((entity_to_str(s), p, entity_to_str(o)))
    # only add entities that are not already in the statement
    result["entities"] = [entity_to_str(e) for e in q.entities if e not in entities_in_statements]

    return result


@app.route("/")
def hello_world():
    logging.info('Invoke Hello World')
    return "<p>Hello, World!</p>"


@app.route('/query')
def query():
    keywords = request.args.get("keywords")
    if not keywords:
        abort(404)
    try:
        print(f'Received keywords: {keywords}')
        print(f'Translating keywords...')
        graph_queries = translation.translate_keyword_query(keyword_query=keywords, verbose=False)
        print(f'{len(graph_queries)} possible queries generated')
        results = {}
        print(f'Sorting...')
        for idx, ranker in enumerate(ranker_strategies):
            results[idx] = {}

            ranked_queries = ranker.rank_queries(graph_queries, data_graph=data_graph)
            if len(ranked_queries) > 0:
                best = ranked_queries[0]
                results[idx] = query_to_json(best)
            else:
                results[idx] = None
        print('Sending results')
        return results

    except:
        abort(404)


with app.test_request_context():
    print(url_for('hello_world'))
    print(url_for('query', keywords="Diabetes Mellitus Metformin treats"))
