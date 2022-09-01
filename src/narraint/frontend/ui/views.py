import ast
import base64
import json
import logging
import os
import sys
import traceback
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from json import JSONDecodeError

import psycopg2
import requests
from PIL import Image
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.gzip import gzip_page
from django.views.generic import TemplateView
from sqlalchemy import func

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, PredicationRating, \
    TagInvertedIndex, SubstitutionGroupRating, EntityKeywords
from narraint.backend.retrieve import retrieve_narrative_documents_from_database
from narraint.config import REPORT_DIR, CHEMBL_ATC_TREE_FILE, MESH_DISEASE_TREE_JSON, BACKEND_CONFIG
from narraint.frontend.entity.autocompletion import AutocompletionUtil
from narraint.frontend.entity.entitytagger import EntityTagger
from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.frontend.ui.search_cache import SearchCache
from narraint.queryengine.aggregation.ontology import ResultAggregationByOntology
from narraint.queryengine.aggregation.substitution_tree import ResultTreeAggregationBySubstitution
from narraint.queryengine.engine import QueryEngine
from narraint.queryengine.logger import QueryLogger
from narraint.queryengine.optimizer import QueryOptimizer
from narraint.queryengine.query import GraphQuery
from narrant.entity.entityresolver import EntityResolver
from narrant.preprocessing.enttypes import DRUG
from narraint.queryengine.log_statistics import create_dictionary_of_logs, get_date_of_today

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)
DO_CACHING = True


class View:
    """
    Singleton encapsulating the former global entity_tagger and cache
    """
    entity_tagger = None
    cache = None

    _instance = None
    initialized = False

    def __init__(self):
        raise RuntimeError('Singleton, use instance() instead')

    @classmethod
    def instance(cls):
        if not cls.initialized:
            cls.initialized = True
            cls._instance = cls.__new__(cls)
            # init resolver here
            cls.query_logger = QueryLogger()
            cls.resolver = EntityResolver.instance()
            cls.entity_tagger = EntityTagger.instance()
            cls.cache = SearchCache()
            cls.autocompletion = AutocompletionUtil.instance()
            cls.translation = QueryTranslation()

        return cls._instance


def get_chembl_indication(request):
    if "drug" not in request.GET:
        return JsonResponse(status=500, data=dict(answer="Drug parameter is missing"))

    try:
        drug_str = str(request.GET['drug']).strip().lower()

        try:
            drug_ids = View.instance().entity_tagger.tag_entity(drug_str)
            drug_ids = list([e.entity_id for e in drug_ids if e.entity_type == DRUG])
            if len(drug_ids) == 0:
                return JsonResponse(status=500, data=dict(answer=f"No drug ids found for term: {drug_str}"))
            with open(BACKEND_CONFIG, 'rt') as f:
                config = json.load(f)
            connection = psycopg2.connect(user=config["POSTGRES_USER"],
                                          password=config["POSTGRES_PW"],
                                          host=config["POSTGRES_HOST"],
                                          port=config["POSTGRES_PORT"],
                                          database="chembldb")
            cursor = connection.cursor()
            # CHEMBL_QUERY = "select mesh_id, max_phase_for_ind from drug_indication where molregno in ((select molregno from molecule_synonyms where synonyms ilike 'Simvastatin') union (select molregno from molecule_dictionary where pref_name ilike 'Simvastatin'))"
            if len(drug_ids) > 1:
                query = "select mesh_id, max_phase_for_ind from drug_indication where molregno in \
                                        (select molregno from molecule_dictionary where chembl_id in %(drugs)s)"
            else:
                query = "select mesh_id, max_phase_for_ind from drug_indication where molregno in \
                                                        (select molregno from molecule_dictionary where chembl_id = %(drugs)s)"
            cursor.execute(query, {"drugs": tuple(drug_ids)})
            records = cursor.fetchall()

            results = []
            for row in records:
                results.append(dict(mesh_id='MESH:' + row[0],
                                    max_phase_for_ind=row[1]))
            connection.close()
            return JsonResponse(dict(results=results))

        except KeyError:
            return JsonResponse(status=500, data=dict(answer=f"No drug ids found for term: {drug_str}"))

    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from PostgreSQL", error)
    return HttpResponse(status=500)


def get_document_graph(request):
    if "document" in request.GET and "data_source" in request.GET:
        document_id = str(request.GET.get("document", "").strip())
        document_collection = str(request.GET.get("data_source", "").strip())
        try:
            start_time = datetime.now()
            document_id = int(document_id)
            session = SessionExtended.get()
            query = session.query(Predication).filter(Predication.document_collection == document_collection)
            query = query.filter(Predication.document_id == document_id)
            query = query.filter(Predication.relation.isnot(None))
            facts = defaultdict(set)
            nodes = set()
            for r in query:
                try:
                    subject_name = View.instance().resolver.get_name_for_var_ent_id(r.subject_id, r.subject_type,
                                                                                    resolve_gene_by_id=False)
                    object_name = View.instance().resolver.get_name_for_var_ent_id(r.object_id, r.object_type,
                                                                                   resolve_gene_by_id=False)
                    subject_name = f'{subject_name} ({r.subject_type})'
                    object_name = f'{object_name} ({r.object_type})'

                    if subject_name < object_name:
                        key = subject_name, r.relation, object_name
                        so_key = subject_name, object_name
                    else:
                        key = object_name, r.relation, subject_name
                        so_key = object_name, subject_name
                    if key not in facts:
                        facts[so_key].add(r.relation)
                        nodes.add(subject_name)
                        nodes.add(object_name)
                except Exception:
                    pass

            result = []
            for (s, o), predicates in facts.items():
                p_txt = []
                for p in predicates:
                    # if there is a more specific edge then associated, ignore it
                    if len(predicates) > 1 and p == "associated":
                        continue
                    p_txt.append(p)
                p_txt = '|'.join([pt for pt in p_txt])
                result.append(dict(s=s, p=p_txt, o=o))
            logging.info(f'Querying document graph for document id: {document_id} - {len(facts)} facts found')
            time_needed = datetime.now() - start_time
            session.remove()
            try:
                View.instance().query_logger.write_document_graph_log(time_needed, document_collection, document_id,
                                                                      len(facts))
            except IOError:
                logging.debug('Could not write document graph log file')

            View.instance().query_logger.write_api_call(True, "get_document_graph", str(request), time_needed)
            return JsonResponse(dict(nodes=list(nodes), facts=result))
        except ValueError:
            View.instance().query_logger.write_api_call(False, "get_document_graph", str(request))
            return JsonResponse(dict(nodes=[], facts=[]))
    else:
        View.instance().query_logger.write_api_call(False, "get_document_graph", str(request))
        return HttpResponse(status=500)


def get_autocompletion(request):
    if "term" in request.GET:
        search_string = str(request.GET.get("term", "").strip())
        completion_terms = []
        if "entity_type" in request.GET:
            entity_type = str(request.GET.get("entity_type", "").strip())
            completion_terms = View.instance().autocompletion.compute_autocompletion_list(search_string,
                                                                                          entity_type=entity_type)
        else:
            completion_terms = View.instance().autocompletion.compute_autocompletion_list(search_string)
        logging.info(f'For {search_string} sending completion terms: {completion_terms}')
        return JsonResponse(dict(terms=completion_terms))
    else:
        return HttpResponse(status=500)


# on a better generation of this json: https://stackoverflow.com/questions/44478515/add-size-x-to-json?noredirect=1&lq=1
def get_tree_info(request):
    if "tree" in request.GET:
        tree = str(request.GET.get("tree").strip()).lower()
        if tree == 'atc':
            with open(CHEMBL_ATC_TREE_FILE, 'r') as inp:
                chembl_atc_tree = json.load(inp)
                return JsonResponse(dict(tree=chembl_atc_tree))
        elif tree == "mesh_disease":
            with open(MESH_DISEASE_TREE_JSON, 'r') as f:
                mesh_disease_tree = json.load(f)
                return JsonResponse(dict(tree=mesh_disease_tree))
    return HttpResponse(status=500)


def get_check_query(request):
    if "query" not in request.GET:
        return JsonResponse(status=500, data=dict(reason="query not given"))
    try:
        search_string = str(request.GET.get("query", "").strip())
        logging.info(f'checking query: {search_string}')
        query_fact_patterns, query_trans_string = View.instance().translation.convert_query_text_to_fact_patterns(
            search_string)
        if query_fact_patterns:
            logging.info('query is valid')
            return JsonResponse(dict(valid="True", query=query_fact_patterns.to_dict()))
        else:
            logging.info(f'query is not valid: {query_trans_string}')
            return JsonResponse(dict(valid="False", query=query_trans_string))
    except Exception:
        return JsonResponse(status=500, data=dict(valid="False", query=None))


def get_term_to_entity(request):
    if "term" not in request.GET:
        return JsonResponse(status=500, data=dict(reason="term not given"))
    try:
        term = str(request.GET.get("term", "").strip()).lower()
        expand_by_prefix = True
        if "expand_by_prefix" in request.GET:
            expand_by_prefix_str = str(request.GET.get("expand_by_prefix", "").strip()).lower()
            if expand_by_prefix_str == "false":
                expand_by_prefix = False
        try:
            entities = View.instance().translation.convert_text_to_entity(term,
                                                                          expand_search_by_prefix=expand_by_prefix)
            return JsonResponse(dict(valid=True, entity=[e.to_dict() for e in entities]))
        except ValueError as e:
            return JsonResponse(dict(valid=False, entity=f'{e}'))
    except Exception as e:
        return JsonResponse(status=500, data=dict(reason="Internal server error"))


def do_query_processing_with_caching(graph_query: GraphQuery, document_collection: str):
    cache_hit = False
    cached_results = None
    start_time = datetime.now()
    if DO_CACHING:
        try:
            cached_results = View.instance().cache.load_result_from_cache(document_collection, graph_query)
            cache_hit = True
        except Exception:
            logging.error('Cannot load query result from cache...')
            cached_results = None
            cache_hit = False
    if DO_CACHING and cached_results:
        logging.info('Cache hit - {} results loaded'.format(len(cached_results)))
        results = cached_results
    else:
        # run query
        results = QueryEngine.process_query_with_expansion(graph_query,
                                                           document_collection_filter={document_collection})
        cache_hit = False
        if DO_CACHING:
            try:
                View.instance().cache.add_result_to_cache(document_collection, graph_query, results)
            except Exception:
                logging.error('Cannot store query result to cache...')
    time_needed = datetime.now() - start_time
    return results, cache_hit, time_needed


@gzip_page
def get_query_narrative_documents(request):
    if "query" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_query_narrative_documents", str(request))
        return JsonResponse(status=500, data=dict(reason="query parameter is missing"))
    if "data_source" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_query_narrative_documents", str(request))
        return JsonResponse(status=500, data=dict(reason="data_source parameter is missing"))

    query = str(request.GET["query"]).strip()
    document_collection = str(request.GET["data_source"]).strip()

    graph_query, query_trans_string = View.instance().translation.convert_query_text_to_fact_patterns(query)
    if not graph_query or len(graph_query.fact_patterns) == 0:
        View.instance().query_logger.write_api_call(False, "get_query_narrative_documents", str(request))
        return JsonResponse(status=500, data=dict(answer="Query not valid", reason=query_trans_string))

    if QueryTranslation.count_variables_in_query(graph_query) != 0:
        View.instance().query_logger.write_api_call(False, "get_query_narrative_documents", str(request))
        return JsonResponse(status=500, data=dict(answer="Does not support queries with variables"))

    try:
        time_start = datetime.now()
        # compute the query
        results, _, _ = do_query_processing_with_caching(graph_query, document_collection)
        result_ids = {r.document_id for r in results}
        # get narrative documents
        session = SessionExtended.get()
        narrative_documents = retrieve_narrative_documents_from_database(session, document_ids=result_ids,
                                                                         document_collection=document_collection)

        View.instance().query_logger.write_api_call(True, "get_query_narrative_documents", str(request),
                                                    time_needed=datetime.now() - time_start)
        return JsonResponse(dict(results=list([nd.to_dict() for nd in narrative_documents])))
    except Exception:
        View.instance().query_logger.write_api_call(False, "get_query_narrative_documents", str(request))
        return JsonResponse(status=500, data=dict(answer="Internal server error"))


@gzip_page
def get_query_document_ids(request):
    if "query" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_query_document_ids", str(request))
        return JsonResponse(status=500, data=dict(reason="query parameter is missing"))
    if "data_source" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_query_document_ids", str(request))
        return JsonResponse(status=500, data=dict(reason="data_source parameter is missing"))

    query = str(request.GET["query"]).strip()
    document_collection = str(request.GET["data_source"]).strip()

    graph_query, query_trans_string = View.instance().translation.convert_query_text_to_fact_patterns(query)
    if not graph_query or len(graph_query.fact_patterns) == 0:
        View.instance().query_logger.write_api_call(False, "get_query_document_ids", str(request))
        return JsonResponse(status=500, data=dict(answer="Query not valid", reason=query_trans_string))

    if QueryTranslation.count_variables_in_query(graph_query) != 0:
        View.instance().query_logger.write_api_call(False, "get_query_document_ids", str(request))
        return JsonResponse(status=500, data=dict(answer="Does not support queries with variables"))

    try:
        time_start = datetime.now()
        # compute the query
        results, _, _ = do_query_processing_with_caching(graph_query, document_collection)
        result_ids = sorted(list({r.document_id for r in results}))
        View.instance().query_logger.write_api_call(True, "get_query_document_ids", str(request),
                                                    time_needed=datetime.now() - time_start)
        return JsonResponse(dict(results=result_ids))
    except Exception:
        View.instance().query_logger.write_api_call(False, "get_query_document_ids", str(request))
        return JsonResponse(status=500, data=dict(answer="Internal server error"))


@gzip_page
def get_narrative_documents(request):
    if "document" not in request.GET and "documents" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_narrative_document", str(request))
        return JsonResponse(status=500, data=dict(reason="document/documents parameter is missing"))
    if "data_source" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_narrative_document", str(request))
        return JsonResponse(status=500, data=dict(reason="data_source parameter is missing"))

    document_ids = set()
    if "document" in request.GET:
        try:
            document_id = int(request.GET["document"].strip())
            document_ids.add(document_id)
        except ValueError:
            View.instance().query_logger.write_api_call(False, "get_narrative_document", str(request))
            return JsonResponse(status=500, data=dict(reason="document must be an integer"))
    elif "documents" in request.GET:
        try:
            document_ids.update([int(did) for did in request.GET["documents"].strip().split(';')])
        except ValueError:
            View.instance().query_logger.write_api_call(False, "get_narrative_document", str(request))
            return JsonResponse(status=500, data=dict(reason="documents must be a list of integer (separated by ;)"))

    document_collection = str(request.GET["data_source"]).strip()
    try:
        time_start = datetime.now()
        # get narrative documents
        session = SessionExtended.get()
        narrative_documents = retrieve_narrative_documents_from_database(session, document_ids=document_ids,
                                                                         document_collection=document_collection)

        View.instance().query_logger.write_api_call(True, "get_narrative_document", str(request),
                                                    time_needed=datetime.now() - time_start)
        return JsonResponse(dict(results=list([nd.to_dict() for nd in narrative_documents])))
    except Exception as e:
        logger.error(f"get_narrative_document: {e}")
        traceback.print_exc()
        View.instance().query_logger.write_api_call(False, "get_narrative_document", str(request))
        return JsonResponse(status=500, data=dict(answer="Internal server error"))


@gzip_page
def get_query_sub_count(request):
    if "query" in request.GET and "data_source" in request.GET:
        query = str(request.GET["query"]).strip()
        document_collection = str(request.GET["data_source"]).strip()
        if document_collection not in ["LitCovid", "LongCovid", "PubMed"]:
            return JsonResponse(status=500,
                                data=dict(answer="data source not valid", reason="Data sources supported: PubMed,"
                                                                                 " LitCovid and LongCovid"))

        graph_query, query_trans_string = View.instance().translation.convert_query_text_to_fact_patterns(query)
        if not graph_query or len(graph_query.fact_patterns) == 0:
            View.instance().query_logger.write_api_call(False, "get_query_sub_count", str(request))
            return JsonResponse(status=500, data=dict(answer="Query not valid", reason=query_trans_string))

        if QueryTranslation.count_variables_in_query(graph_query) != 1:
            View.instance().query_logger.write_api_call(False, "get_query_sub_count", str(request))
            return JsonResponse(status=500, data=dict(answer="query must have one variable"))

        time_start = datetime.now()
        # compute the query
        results, _, _ = do_query_processing_with_caching(graph_query, document_collection)

        # next get the aggregation by var names
        substitution_aggregation = ResultTreeAggregationBySubstitution()
        results_ranked, is_aggregate = substitution_aggregation.rank_results(results, freq_sort_desc=True)

        # generate a list of [(ent_id, ent_name, doc_count), ...]
        sub_count_list = list()
        # go through all aggregated results
        for aggregate in results_ranked.results:
            var2sub = aggregate.var2substitution
            # get the first substitution
            var_name, sub = next(iter(var2sub.items()))
            sub_count_list.append(dict(id=sub.entity_id,
                                       name=sub.entity_name,
                                       count=aggregate.get_result_size()))

        View.instance().query_logger.write_api_call(True, "get_query_sub_count", str(request),
                                                    time_needed=datetime.now() - time_start)
        # send results back
        return JsonResponse(dict(sub_count_list=sub_count_list))
    else:
        View.instance().query_logger.write_api_call(False, "get_query_sub_count", str(request))
        return HttpResponse(status=500)


def get_document_ids_for_entity(request):
    if "entity_id" not in request.GET or "entity_type" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_document_ids_for_entity", str(request))
        return JsonResponse(status=500, data=dict(reason="entity_id and entity_type are required parameters"))
    if "data_source" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_document_ids_for_entity", str(request))
        return JsonResponse(status=500, data=dict(reason="data_source parameter is missing"))

    try:
        time_start = datetime.now()
        entity_id, entity_type = str(request.GET["entity_id"]).strip(), str(request.GET["entity_type"]).strip()
        document_collection = str(request.GET["data_source"]).strip()

        # Query Database for all document ids that contain this entity
        session = SessionExtended.get()
        query = session.query(TagInvertedIndex.document_ids) \
            .filter(TagInvertedIndex.document_collection == document_collection) \
            .filter(TagInvertedIndex.entity_id == entity_id) \
            .filter(TagInvertedIndex.entity_type == entity_type)

        # execute query and get result (query can only have one result due to querying the PK)
        row = query.first()
        if row:
            # interpret the string from db as a python list
            document_ids = ast.literal_eval(row[0])
        else:
            document_ids = []
        session.remove()
        View.instance().query_logger.write_api_call(True, "get_document_ids_for_entity", str(request),
                                                    time_needed=datetime.now() - time_start)
        # send results back
        return JsonResponse(dict(document_ids=document_ids))

    except Exception as e:
        logger.error(f"get_document_ids_for_entity: {e}")
        traceback.print_exc()
        View.instance().query_logger.write_api_call(False, "get_document_ids_for_entity", str(request))
        return JsonResponse(status=500, data=dict(answer="Internal server error"))


# invokes Django to compress the results
@gzip_page
def get_query(request):
    results_converted = []
    is_aggregate = False
    valid_query = False
    query_limit_hit = False
    query_trans_string = ""
    if "query" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_query", str(request))
        return JsonResponse(status=500, data=dict(reason="query parameter is missing"))
    if "data_source" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_query", str(request))
        return JsonResponse(status=500, data=dict(reason="data_source parameter is missing"))

    try:
        query = str(request.GET.get("query", "").strip())
        data_source = str(request.GET.get("data_source", "").strip())
        if "outer_ranking" in request.GET:
            outer_ranking = str(request.GET.get("outer_ranking", "").strip())
        else:
            outer_ranking = "outer_ranking_substitution"

        if "start_pos" in request.GET:
            start_pos = request.GET.get("start_pos").strip()
            try:
                start_pos = int(start_pos)
            except ValueError:
                start_pos = None
        else:
            start_pos = None
        if "end_pos" in request.GET:
            end_pos = request.GET.get("end_pos").strip()
            try:
                end_pos = int(end_pos)
            except ValueError:
                end_pos = None
        else:
            end_pos = None

        if "freq_sort" in request.GET:
            freq_sort_desc = str(request.GET.get("freq_sort", "").strip())
            if freq_sort_desc == 'False':
                freq_sort_desc = False
            else:
                freq_sort_desc = True
        else:
            freq_sort_desc = True

        if "year_sort" in request.GET:
            year_sort_desc = str(request.GET.get("year_sort", "").strip())
            if year_sort_desc == 'False':
                year_sort_desc = False
            else:
                year_sort_desc = True
        else:
            year_sort_desc = True

        # inner_ranking = str(request.GET.get("inner_ranking", "").strip())
        logging.info(f'Query string is: {query}')
        logging.info("Selected data source is {}".format(data_source))
        logging.info('Strategy for outer ranking: {}'.format(outer_ranking))
        # logging.info('Strategy for inner ranking: {}'.format(inner_ranking))
        time_start = datetime.now()
        graph_query, query_trans_string = View.instance().translation.convert_query_text_to_fact_patterns(
            query)
        if data_source not in ["LitCovid", "LongCovid", "PubMed", "ZBMed"]:
            results_converted = []
            query_trans_string = "Data source is unknown"
            logger.error('parsing error')
        elif outer_ranking not in ["outer_ranking_substitution", "outer_ranking_ontology"]:
            query_trans_string = "Outer ranking strategy is unknown"
            logger.error('parsing error')
        elif not graph_query or len(graph_query.fact_patterns) == 0:
            results_converted = []
            logger.error('parsing error')
        elif outer_ranking == 'outer_ranking_ontology' and QueryTranslation.count_variables_in_query(
                graph_query) > 1:
            results_converted = []
            nt_string = ""
            query_trans_string = "Do not support multiple variables in an ontology-based ranking"
            logger.error("Do not support multiple variables in an ontology-based ranking")
        else:
            logger.info(f'Translated Query is: {str(graph_query)}')
            valid_query = True
            document_collection = data_source

            results, cache_hit, time_needed = do_query_processing_with_caching(graph_query, document_collection)
            result_ids = {r.document_id for r in results}
            opt_query = QueryOptimizer.optimize_query(graph_query)
            View.instance().query_logger.write_query_log(time_needed, document_collection, cache_hit, len(result_ids),
                                                         query, opt_query)
            results_converted = []
            if outer_ranking == 'outer_ranking_substitution':
                substitution_aggregation = ResultTreeAggregationBySubstitution()
                sorted_var_names = graph_query.get_var_names_in_order()
                results_ranked, is_aggregate = substitution_aggregation.rank_results(results, sorted_var_names,
                                                                                     freq_sort_desc, year_sort_desc,
                                                                                     start_pos, end_pos)
                results_converted = results_ranked.to_dict()
            elif outer_ranking == 'outer_ranking_ontology':
                substitution_ontology = ResultAggregationByOntology()
                results_ranked, is_aggregate = substitution_ontology.rank_results(results, freq_sort_desc,
                                                                                  year_sort_desc)
                results_converted = results_ranked.to_dict()

        View.instance().query_logger.write_api_call(True, "get_query", str(request),
                                                    time_needed=datetime.now() - time_start)
        return JsonResponse(
            dict(valid_query=valid_query, is_aggregate=is_aggregate, results=results_converted,
                 query_translation=query_trans_string,
                 query_limit_hit="False"))
    except Exception:
        View.instance().query_logger.write_api_call(False, "get_query", str(request))
        query_trans_string = "keyword query cannot be converted (syntax error)"
        traceback.print_exc(file=sys.stdout)
        return JsonResponse(
            dict(valid_query="", results=[], query_translation=query_trans_string, query_limit_hit="False"))


# invokes Django to compress the results
@gzip_page
def get_new_query(request):
    results_converted = []
    is_aggregate = False
    valid_query = False
    query_limit_hit = False
    query_trans_string = ""
    if "query" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_new_query", str(request))
        return JsonResponse(status=500, data=dict(reason="query parameter is missing"))
    if "data_source" not in request.GET:
        View.instance().query_logger.write_api_call(False, "get_new_query", str(request))
        return JsonResponse(status=500, data=dict(reason="data_source parameter is missing"))

    try:
        query = str(request.GET.get("query", "").strip())
        data_source = str(request.GET.get("data_source", "").strip())

        if "entities" in request.GET:
            req_entities = str(request.GET.get("entities", "").strip()).split(";")
        else:
            req_entities = None

        if "outer_ranking" in request.GET:
            outer_ranking = str(request.GET.get("outer_ranking", "").strip())
        else:
            outer_ranking = "outer_ranking_substitution"

        if "start_pos" in request.GET:
            start_pos = request.GET.get("start_pos").strip()
            try:
                start_pos = int(start_pos)
            except ValueError:
                start_pos = None
        else:
            start_pos = None
        if "end_pos" in request.GET:
            end_pos = request.GET.get("end_pos").strip()
            try:
                end_pos = int(end_pos)
            except ValueError:
                end_pos = None
        else:
            end_pos = None

        if "freq_sort" in request.GET:
            freq_sort_desc = str(request.GET.get("freq_sort", "").strip())
            if freq_sort_desc == 'False':
                freq_sort_desc = False
            else:
                freq_sort_desc = True
        else:
            freq_sort_desc = True

        if "year_sort" in request.GET:
            year_sort_desc = str(request.GET.get("year_sort", "").strip())
            if year_sort_desc == 'False':
                year_sort_desc = False
            else:
                year_sort_desc = True
        else:
            year_sort_desc = True

        # inner_ranking = str(request.GET.get("inner_ranking", "").strip())
        logging.info(f'Query string is: {query}')
        logging.info(f'Additional entities are {req_entities}')
        logging.info("Selected data source is {}".format(data_source))
        logging.info('Strategy for outer ranking: {}'.format(outer_ranking))
        # logging.info('Strategy for inner ranking: {}'.format(inner_ranking))
        time_start = datetime.now()

        graph_query, query_trans_string = View.instance().translation \
            .convert_query_text_to_fact_patterns(query)
        if data_source not in ["LitCovid", "LongCovid", "PubMed", "ZBMed"]:
            results_converted = []
            query_trans_string = "Data source is unknown"
            logger.error('parsing error')
        elif outer_ranking not in ["outer_ranking_substitution", "outer_ranking_ontology"]:
            query_trans_string = "Outer ranking strategy is unknown"
            logger.error('parsing error')
        elif not graph_query or len(graph_query.fact_patterns) == 0:
            results_converted = []
            logger.error('parsing error')
        elif outer_ranking == 'outer_ranking_ontology' and QueryTranslation.count_variables_in_query(
                graph_query) > 1:
            results_converted = []
            nt_string = ""
            query_trans_string = "Do not support multiple variables in an ontology-based ranking"
            logger.error("Do not support multiple variables in an ontology-based ranking")
        else:
            # search for all documents containing all additional entities
            if req_entities is not None:
                for re in req_entities:
                    try:
                        entity_ids = View.instance().translation.convert_text_to_entity(re)
                        graph_query.add_additional_entities(list(entity_ids))
                    except ValueError:
                        logging.debug(f'No conversion found for {re}')
                        continue

            logger.info(f'Translated Query is: {str(graph_query)}')
            valid_query = True
            document_collection = data_source

            results, cache_hit, time_needed = \
                do_query_processing_with_caching(graph_query, document_collection)
            result_ids = {r.document_id for r in results}
            opt_query = QueryOptimizer.optimize_query(graph_query)
            View.instance().query_logger.write_query_log(time_needed, document_collection, cache_hit, len(result_ids),
                                                         query, opt_query)
            results_converted = []
            if outer_ranking == 'outer_ranking_substitution':
                substitution_aggregation = ResultTreeAggregationBySubstitution()
                sorted_var_names = graph_query.get_var_names_in_order()
                results_ranked, is_aggregate = substitution_aggregation.rank_results(results, sorted_var_names,
                                                                                     freq_sort_desc, year_sort_desc,
                                                                                     start_pos, end_pos)
                results_converted = results_ranked.to_dict()
            elif outer_ranking == 'outer_ranking_ontology':
                substitution_ontology = ResultAggregationByOntology()
                results_ranked, is_aggregate = substitution_ontology.rank_results(results, freq_sort_desc,
                                                                                  year_sort_desc)
                results_converted = results_ranked.to_dict()

        View.instance().query_logger.write_api_call(True, "get_query", str(request),
                                                    time_needed=datetime.now() - time_start)
        return JsonResponse(
            dict(valid_query=valid_query, is_aggregate=is_aggregate, results=results_converted,
                 query_translation=query_trans_string,
                 query_limit_hit="False"))
    except Exception:
        View.instance().query_logger.write_api_call(False, "get_query", str(request))
        query_trans_string = "keyword query cannot be converted (syntax error)"
        traceback.print_exc(file=sys.stdout)
        return JsonResponse(
            dict(valid_query="", results=[], query_translation=query_trans_string, query_limit_hit="False"))


def get_provenance(request):
    if "prov" in request.GET and "document_id" in request.GET and "data_source" in request.GET:
        try:
            document_id = str(request.GET["document_id"]).strip()
            document_collection = str(request.GET["data_source"]).strip()
            time_start = datetime.now()

            start = datetime.now()
            fp2prov_ids = json.loads(str(request.GET.get("prov", "").strip()))
            result = QueryEngine.query_provenance_information(fp2prov_ids)

            time_needed = datetime.now() - start
            predication_ids = set()
            for _, pred_ids in fp2prov_ids.items():
                predication_ids.update(pred_ids)
            try:
                View.instance().query_logger.write_provenance_log(time_needed, document_collection, document_id,
                                                                  predication_ids)
            except IOError:
                logging.debug('Could not write provenance log file')

            View.instance().query_logger.write_api_call(True, "get_provenance", str(request),
                                                        time_needed=datetime.now() - start)
            return JsonResponse(dict(result=result.to_dict()))
        except Exception:
            View.instance().query_logger.write_api_call(False, "get_provenance", str(request))
            traceback.print_exc(file=sys.stdout)
            return HttpResponse(status=500)
    else:
        View.instance().query_logger.write_api_call(False, "get_provenance", str(request))
        return HttpResponse(status=500)


def post_feedback(request):
    data = None  # init needed for second evaluation step
    try:
        data = json.loads(request.body)
    except JSONDecodeError:
        logging.debug('Invalid JSON received')
        return HttpResponse(status=500)

    if data and data.keys() & {"query", "rating", "userid", "predicationids"}:
        try:
            time_start = datetime.now()
            predication_ids = data["predicationids"]
            query = data["query"]
            rating = data["rating"]
            userid = data["userid"]

            session = SessionExtended.get()
            for pred_id in predication_ids.split(','):
                PredicationRating.insert_user_rating(session, userid, query, int(pred_id), rating)

            logging.info(f'User "{userid}" has rated "{predication_ids}" as "{rating}"')
            try:
                View.instance().query_logger.write_rating(query, userid, predication_ids)
            except IOError:
                logging.debug('Could not write rating log file')
            View.instance().query_logger.write_api_call(True, "get_feedback", str(request),
                                                        time_needed=datetime.now() - time_start)
            return HttpResponse(status=200)
        except Exception:
            View.instance().query_logger.write_api_call(False, "get_feedback", str(request))
            traceback.print_exc(file=sys.stdout)
            return HttpResponse(status=500)
    View.instance().query_logger.write_api_call(False, "get_feedback", str(request))
    return HttpResponse(status=500)


def post_subgroup_feedback(request):
    data = None  # init needed for second evaluation step
    try:
        data = json.loads(request.body)
    except JSONDecodeError:
        logging.debug('Invalid JSON received')
        return HttpResponse(status=500)

    if data and data.keys() & {"variable_name", "entity_id", "entity_type", "query", "rating", "userid"}:
        try:
            time_start = datetime.now()
            variable_name = data["variable_name"]
            entity_name = data["entity_name"]
            entity_id = data["entity_id"]
            entity_type = data["entity_type"]
            query = data["query"]
            rating = data["rating"]
            userid = data["userid"]

            session = SessionExtended.get()

            SubstitutionGroupRating.insert_sub_group_user_rating(
                session, userid, query, variable_name, entity_name, entity_id,
                entity_type, rating)

            logging.info(f'User "{userid}" has rated "{variable_name}":'
                         f'[{entity_name}, {entity_id}, {entity_type}] as "{rating}"')
            try:
                View.instance().query_logger.write_subgroup_rating_log(
                    query, userid, variable_name, entity_name, entity_id, entity_type)
            except IOError:
                logging.debug('Could not write rating log file')
            View.instance().query_logger.write_api_call(True, "get_subgroup_feedback", str(request),
                                                        time_needed=datetime.now() - time_start)
            return HttpResponse(status=200)
        except Exception:
            View.instance().query_logger.write_api_call(False, "get_subgroup_feedback", str(request))
            traceback.print_exc(file=sys.stdout)
            return HttpResponse(status=500)

    View.instance().query_logger.write_api_call(False, "get_subgroup_feedback", str(request))
    return HttpResponse(status=500)


def post_document_link_clicked(request):
    data = None
    try:
        data = json.loads(request.body)
    except JSONDecodeError:
        logging.debug('Invalid JSON received')
        View.instance().query_logger.write_api_call(False, "document_clicked", str(request))
        return HttpResponse(status=500)

    if data and data.keys() & {"query", "document_id", "link", "data_source"}:
        query = data["query"]
        document_id = data["document_id"]
        document_collection = data["data_source"]
        link = data["link"]
        try:
            View.instance().query_logger.write_document_link_clicked(query, document_collection, document_id, link)
        except IOError:
            View.instance().query_logger.write_api_call(False, "document_clicked", str(request))
            return HttpResponse(status=500)
        View.instance().query_logger.write_api_call(True, "document_clicked", str(request))
        return HttpResponse(status=200)
    View.instance().query_logger.write_api_call(False, "document_clicked", str(request))
    return HttpResponse(status=500)


def post_paper_view_log(request):
    data = None
    try:
        data = json.loads(request.body)
    except JSONDecodeError:
        View.instance().query_logger.write_api_call(False, "paper_view_log", str(request))
        return HttpResponse(status=500)

    if data and data.keys() & {"doc_id", "doc_collection"}:
        doc_id = data["doc_id"]
        doc_collection = data["doc_collection"]

        try:
            View.instance().query_logger.write_paper_view(doc_id, doc_collection)
        except IOError:
            View.instance().query_logger.write_api_call(False, "paper_view_log", str(request))
            return HttpResponse(status=500)

        View.instance().query_logger.write_api_call(True, "paper_view_log", str(request))
        return HttpResponse(status=200)
    View.instance().query_logger.write_api_call(False, "paper_view_log", str(request))
    return HttpResponse(status=500)


def post_drug_ov_search_log(request):
    data = None  # init needed for second evaluation step
    try:
        data = json.loads(request.body)
    except JSONDecodeError:
        logging.debug('Invalid JSON received')
        return HttpResponse(status=500)

    if data and data.keys() & {"drug"}:
        drug = data["drug"]
        try:
            View.instance().query_logger.write_drug_ov_search(drug)
        except IOError:
            logging.debug('Could not write drug searched log file')
        return HttpResponse(status=200)
    return HttpResponse(status=500)


def get_logs_data(request):
    try:
        return JsonResponse(LogsView.data_dict)
    except:
        return HttpResponse(status=500)


def post_drug_ov_subst_href_log(request):
    data = None  # init needed for second evaluation step
    try:
        data = json.loads(request.body)
    except JSONDecodeError:
        logging.debug('Invalid JSON received')
        return HttpResponse(status=500)

    if data and data.keys() & {"drug", "substance", "query"}:
        drug = data["drug"]
        substance = data["substance"]
        query = data["query"]
        try:
            View.instance().query_logger.write_drug_ov_substance_href(drug, substance, query)
        except IOError:
            logging.debug('Could not write substance href log file')
        return HttpResponse(status=200)
    return HttpResponse(status=500)


def post_drug_ov_chembl_phase_href_log(request):
    data = None  # init needed for second evaluation step
    try:
        data = json.loads(request.body)
    except JSONDecodeError:
        logging.debug('Invalid JSON received')
        return HttpResponse(status=500)

    if data and data.keys() & {"drug", "disease_name", "disease_id", "query", "phase"}:
        drug = data["drug"]
        disease_name = data["disease_name"]
        disease_id = data["disease_id"]
        phase = data["phase"]
        query = data["query"]
        try:
            View.instance().query_logger.write_drug_ov_chembl_phase_href(drug, disease_name, disease_id, phase, query)
        except IOError:
            logging.debug('Could not write chembl phase href log file')
        return HttpResponse(status=200)
    return HttpResponse(status=500)


def post_report(request):
    try:
        req_data = json.loads(request.body.decode("utf-8"))
        report_description = req_data.get("description", "")
        report_img_64 = req_data.get("img64", "")
        report_path = os.path.join(REPORT_DIR, f"{datetime.now():%Y-%m-%d_%H:%M:%S}")
        os.makedirs(report_path, exist_ok=True)
        with open(os.path.join(report_path, "description.txt"), "w+") as f:
            f.write(report_description)
        img = Image.open(BytesIO(base64.b64decode(report_img_64[22:])))
        img.save(os.path.join(report_path, "screenshot.png"), 'PNG')
        return HttpResponse(status=200)

    except:
        traceback.print_exc(file=sys.stdout)
        return HttpResponse(status=500)


def get_keywords(request):
    if request.GET.keys() & {"substance_id"}:
        substance_id = request.GET.get("substance_id", "")
        try:
            session = SessionExtended.get()
            query = session.query(EntityKeywords.keyword_data).filter(EntityKeywords.entity_id == substance_id)
            result = query.first()

            keywords = ""
            if result:
                keywords = ast.literal_eval(result[0])
            return JsonResponse(dict(keywords=keywords))

        except Exception:
            logging.debug(f"Could not retrieve keywords for {substance_id}")
    return HttpResponse(status=500)


class SearchView(TemplateView):
    template_name = "ui/search.html"

    def __init__(self):
        init_view = View.instance()
        super(SearchView, self).__init__()

    def get(self, request, *args, **kwargs):
        View.instance().query_logger.write_page_view_log(SearchView.template_name)
        return super().get(request, *args, **kwargs)


class NewSearchView(TemplateView):
    template_name = "ui/new_search.html"

    def __init__(self):
        init_view = View.instance()
        super(NewSearchView, self).__init__()

    def get(self, request, *args, **kwargs):
        View.instance().query_logger.write_page_view_log(
            NewSearchView.template_name)
        return super().get(request, *args, **kwargs)


class SwaggerUIView(TemplateView):
    template_name = "ui/swagger-ui.html"


class LogsView(TemplateView):
    template_name = "ui/logs.html"
    log_date = None
    data_dict = None

    def get(self, request, *args, **kwargs):
        View.instance().query_logger.write_page_view_log(LogsView.template_name)
        if not LogsView.log_date or LogsView.log_date != get_date_of_today() or not LogsView.data_dict:
            try:
                logger.debug("Computing logs")
                LogsView.data_dict = create_dictionary_of_logs()
                LogsView.log_date = get_date_of_today()
                logger.debug("Logs computed")
            except:
                traceback.print_exc(file=sys.stdout)
        return super().get(request, *args, **kwargs)


class StatsView(TemplateView):
    template_name = "ui/stats.html"
    stats_query_results = None

    def get(self, request, *args, **kwargs):
        View.instance().query_logger.write_page_view_log(StatsView.template_name)
        if request.is_ajax():
            if "query" in request.GET:
                if not StatsView.stats_query_results:
                    session = SessionExtended.get()
                    try:
                        logging.info('Processing database statistics...')
                        query = session.query(Predication.relation, Predication.extraction_type,
                                              func.count(Predication.relation)). \
                            group_by(Predication.relation).group_by(Predication.extraction_type).all()
                        results = list()
                        for r in query:
                            results.append((r[0], r[1], r[2]))
                        StatsView.stats_query_results = results
                    except:
                        traceback.print_exc(file=sys.stdout)
                    session.close()
                return JsonResponse(
                    dict(results=StatsView.stats_query_results)
                )
        return super().get(request, *args, **kwargs)


class HelpView(TemplateView):
    template_name = "ui/help.html"

    def get(self, request, *args, **kwargs):
        View.instance().query_logger.write_page_view_log(HelpView.template_name)
        return super().get(request, *args, **kwargs)


class DocumentView(TemplateView):
    template_name = "ui/paper.html"

    def get(self, request, *args, **kwargs):
        View.instance().query_logger.write_page_view_log(DocumentView.template_name)
        return super().get(request, *args, **kwargs)


class DrugOverviewIndexView(TemplateView):
    template_name = "ui/drug_overview_index.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class DrugOverviewView(TemplateView):
    template_name = "ui/drug_overview.html"


# invokes Django to compress the results
@gzip_page
def get_ps_query(request):
    if request.GET.keys() & {"query", "confidence", "sources"}:
        query = request.GET["query"].strip()
        confidence = request.GET["confidence"]
        sources = request.GET["sources"]
        if "statement" in request.GET:
            statement = request.GET["statement"]
        else:
            statement = None
        try:
            confidence = float(confidence)
            logging.info('Received political sciences query...')
            logging.info(f'Search with conf. {confidence} for query: {query}')
            if statement:
                logging.info(f'Use statement "{statement}"')
            logging.info(f'Sources: {sources}')
            nd_result = requests.get(
                f"http://127.0.0.1:5050//query?confidence={confidence}&sources={sources}&query_str={query}&statement={statement}")
            json_data = nd_result.json()
            if nd_result.status_code == 200:
                return JsonResponse(status=200, data=json_data)
        except ValueError:
            return JsonResponse(status=500, data=dict(reason=f"confidence must be a float (not {confidence}"))
    else:
        return JsonResponse(status=500, data=dict(reason="query or confidence are missing"))


class PoliticalSciencesView(TemplateView):
    template_name = "ui/political_sciences.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


logging.info('Initialize view')
View.instance()
