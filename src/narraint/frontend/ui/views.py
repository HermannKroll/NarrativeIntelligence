import ast
import base64
import json
import logging
import os
import sys
import traceback
from collections import defaultdict
from datetime import datetime
from json import JSONDecodeError

from django.http import JsonResponse, HttpResponse
from django.views.decorators.gzip import gzip_page
from django.views.generic import TemplateView
from sqlalchemy import func
from sqlalchemy.exc import OperationalError

from kgextractiontoolbox.backend.retrieve import retrieve_narrative_documents_from_database
from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, TagInvertedIndex, EntityKeywords, DrugDiseaseTrialPhase, \
    DatabaseUpdate, Sentence
from narraint.config import FEEDBACK_REPORT_DIR, CHEMBL_ATC_TREE_FILE, MESH_DISEASE_TREE_JSON, FEEDBACK_PREDICATION_DIR, \
    FEEDBACK_SUBGROUP_DIR, LOG_DIR, FEEDBACK_CLASSIFICATION
from narraint.frontend.entity.autocompletion import AutocompletionUtil
from narraint.frontend.entity.entityexplainer import EntityExplainer
from narraint.frontend.entity.entitytagger import EntityTagger
from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.frontend.filter.classification_filter import ClassificationFilter
from narraint.frontend.filter.data_sources_filter import DataSourcesFilter
from narraint.frontend.filter.time_filter import TimeFilter
from narraint.frontend.filter.title_filter import TitleFilter
from narraint.frontend.ui.search_cache import SearchCache
from narraint.keywords2graph.translation import Keyword2GraphTranslation
from narraint.queryengine.aggregation.ontology import ResultAggregationByOntology
from narraint.queryengine.aggregation.substitution_tree import ResultTreeAggregationBySubstitution
from narraint.queryengine.engine import QueryEngine
from narraint.queryengine.logger import QueryLogger
from narraint.queryengine.optimizer import QueryOptimizer
from narraint.queryengine.query import GraphQuery
from narraint.queryengine.result import QueryDocumentResult, QueryDocumentResultList
from narraint.ranking.corpus import DocumentCorpus
from narraint.ranking.indexed_document import IndexedDocument
from narraint.recommender.recommendation import RecommendationSystem
from narrant.entity.entityresolver import EntityResolver

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)
DO_CACHING = True


class View:
    """
    Singleton encapsulating the former global entity_tagger and cache
    """
    entity_tagger = None
    cache = None
    explainer = None

    _instance = None
    initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # init resolver here
            cls.query_logger = QueryLogger()
            cls.resolver = EntityResolver()
            cls.entity_tagger = EntityTagger()
            cls.cache = SearchCache()
            cls.autocompletion = AutocompletionUtil()
            cls.translation = QueryTranslation()
            cls.explainer = EntityExplainer()
            cls.keyword2graph = Keyword2GraphTranslation()
            cls.corpus = DocumentCorpus()
            cls.recommender = RecommendationSystem()
        return cls._instance


def get_document_graph(request):
    if "document" in request.GET and "data_source" in request.GET:
        document_id = str(request.GET.get("document", "").strip())
        document_collection = str(request.GET.get("data_source", "").strip())

        try:
            start_time = datetime.now()
            document_id = int(document_id)
            session = SessionExtended.get()

            # retrieve all document information from DB
            narrative_documents = retrieve_narrative_documents_from_database(session, document_ids={document_id},
                                                                             document_collection=document_collection)

            if len(narrative_documents) != 1:
                View().query_logger.write_api_call(False, "get_document_graph", str(request))
                return JsonResponse(status=500, data=dict(reason="No document data available", nodes=[], facts=[]))

            # index the document to compute frequency and coverage
            indexed_document = IndexedDocument(narrative_documents[0])
            # score all edge and sort them
            sorted_extracted_statements = [(s, View().corpus.score_edge_by_tf_and_concept_idf(s, indexed_document))
                                           for s in indexed_document.extracted_statements]
            sorted_extracted_statements.sort(key=lambda x: x[1], reverse=True)

            sentence_ids = set(s.sentence_id for (s, _) in sorted_extracted_statements)
            sentence_id2text = QueryEngine.query_sentences_for_sent_ids(sentence_ids)

            facts = defaultdict(set)
            facts2text = dict()
            facts2score = dict()
            nodes = set()
            # translate + aggregate edges
            for stmt, score in sorted_extracted_statements:
                try:
                    subject_name = View().resolver.get_name_for_var_ent_id(stmt.subject_id, stmt.subject_type,
                                                                           resolve_gene_by_id=False)
                    object_name = View().resolver.get_name_for_var_ent_id(stmt.object_id, stmt.object_type,
                                                                          resolve_gene_by_id=False)
                    subject_name = f'{subject_name} ({stmt.subject_type})'
                    object_name = f'{object_name} ({stmt.object_type})'

                    if subject_name < object_name:
                        key = subject_name, stmt.relation, object_name
                        so_key = subject_name, object_name
                    else:
                        key = object_name, stmt.relation, subject_name
                        so_key = object_name, subject_name
                    # This code aggregates facts by predicates
                    # Only one edge between two nodes is shown but labels are concatenated
                    if key not in facts:
                        facts[so_key].add(stmt.relation)
                        if so_key in facts2score:
                            facts2score[so_key] = max(score, facts2score[so_key])
                        else:
                            facts2score[so_key] = score
                        nodes.add(subject_name)
                        nodes.add(object_name)

                    # Map the fact to the corresponding sentence text
                    facts2text[so_key] = sentence_id2text[stmt.sentence_id]
                except Exception:
                    pass

            scored_results = []
            # This code aggregates facts by predicates
            # Only one edge between two nodes is shown but labels are concatenated
            for (s, o), predicates in facts.items():
                p_txt = []
                for p in predicates:
                    # if there is a more specific edge then associated, ignore it
                    if len(predicates) > 1 and p == "associated":
                        continue
                    p_txt.append(p)
                p_txt = '|'.join([pt for pt in p_txt])
                scored_results.append(dict(s=s, p=p_txt, o=o, score=facts2score[(s, o)], text=facts2text[(s, o)]))
            # sort results by score descending
            scored_results.sort(key=lambda x: x["score"], reverse=True)
            logging.info(f'Querying document graph for document id: {document_id} - {len(facts)} facts found')
            time_needed = datetime.now() - start_time
            session.remove()
            try:
                View().query_logger.write_document_graph_log(time_needed, document_collection, document_id,
                                                             len(facts))
            except IOError:
                logging.debug('Could not write document graph log file')

            View().query_logger.write_api_call(True, "get_document_graph", str(request), time_needed)
            return JsonResponse(dict(nodes=list(nodes), facts=scored_results))
        except ValueError:
            View().query_logger.write_api_call(False, "get_document_graph", str(request))
            return JsonResponse(dict(nodes=[], facts=[]))
    else:
        View().query_logger.write_api_call(False, "get_document_graph", str(request))
        return HttpResponse(status=500)


def get_autocompletion(request):
    if "term" in request.GET:
        search_string = str(request.GET.get("term", "").strip())
        completion_terms = []
        if "entity_type" in request.GET:
            entity_type = str(request.GET.get("entity_type", "").strip())
            completion_terms = View().autocompletion.compute_autocompletion_list(search_string,
                                                                                 entity_type=entity_type)
        else:
            completion_terms = View().autocompletion.compute_autocompletion_list(search_string)
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
        query_fact_patterns, query_trans_string = View().translation.convert_query_text_to_fact_patterns(
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
            entities = View().translation.convert_text_to_entity(term,
                                                                 expand_search_by_prefix=expand_by_prefix)
            resolver = EntityResolver()
            for e in entities:
                try:
                    e.entity_name = resolver.get_name_for_var_ent_id(e.entity_id, e.entity_type)
                except KeyError:
                    e.entity_name = ""
            return JsonResponse(dict(valid=True, entity=[e.to_dict() for e in entities]))
        except ValueError as e:
            return JsonResponse(dict(valid=False, entity=f'{e}'))
    except Exception as e:
        return JsonResponse(status=500, data=dict(reason="Internal server error"))


def do_query_processing_with_caching(graph_query: GraphQuery, document_collections: set):
    cache_hit = False
    cached_results = None
    start_time = datetime.now()
    collection_string = "-".join(sorted(document_collections))
    if DO_CACHING:
        try:
            cached_results = View().cache.load_result_from_cache(collection_string, graph_query)
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
                                                           document_collection_filter=document_collections)
        cache_hit = False
        if DO_CACHING:
            try:

                View().cache.add_result_to_cache(collection_string, graph_query, results)
            except Exception:
                logging.error('Cannot store query result to cache...')
    time_needed = datetime.now() - start_time
    return results, cache_hit, time_needed


@gzip_page
def get_query_narrative_documents(request):
    if "query" not in request.GET:
        View().query_logger.write_api_call(False, "get_query_narrative_documents", str(request))
        return JsonResponse(status=500, data=dict(reason="query parameter is missing"))
    if "data_source" not in request.GET:
        View().query_logger.write_api_call(False, "get_query_narrative_documents", str(request))
        return JsonResponse(status=500, data=dict(reason="data_source parameter is missing"))

    query = str(request.GET["query"]).strip()
    document_collection = str(request.GET["data_source"]).strip()

    graph_query, query_trans_string = View().translation.convert_query_text_to_fact_patterns(query)
    if not graph_query or len(graph_query.fact_patterns) == 0:
        View().query_logger.write_api_call(False, "get_query_narrative_documents", str(request))
        return JsonResponse(status=500, data=dict(answer="Query not valid", reason=query_trans_string))

    if QueryTranslation.count_variables_in_query(graph_query) != 0:
        View().query_logger.write_api_call(False, "get_query_narrative_documents", str(request))
        return JsonResponse(status=500, data=dict(answer="Does not support queries with variables"))

    try:
        time_start = datetime.now()
        # compute the query
        results, _, _ = do_query_processing_with_caching(graph_query, {document_collection})
        result_ids = {r.document_id for r in results}
        # get narrative documents
        session = SessionExtended.get()
        narrative_documents = retrieve_narrative_documents_from_database(session, document_ids=result_ids,
                                                                         document_collection=document_collection)

        View().query_logger.write_api_call(True, "get_query_narrative_documents", str(request),
                                           time_needed=datetime.now() - time_start)
        return JsonResponse(dict(results=list([nd.to_dict() for nd in narrative_documents])))
    except Exception:
        View().query_logger.write_api_call(False, "get_query_narrative_documents", str(request))
        return JsonResponse(status=500, data=dict(answer="Internal server error"))


@gzip_page
def get_query_document_ids(request):
    if "query" not in request.GET:
        View().query_logger.write_api_call(False, "get_query_document_ids", str(request))
        return JsonResponse(status=500, data=dict(reason="query parameter is missing"))
    if "data_source" not in request.GET:
        View().query_logger.write_api_call(False, "get_query_document_ids", str(request))
        return JsonResponse(status=500, data=dict(reason="data_source parameter is missing"))

    query = str(request.GET["query"]).strip()
    document_collection = str(request.GET["data_source"]).strip()

    graph_query, query_trans_string = View().translation.convert_query_text_to_fact_patterns(query)
    if not graph_query or len(graph_query.fact_patterns) == 0:
        View().query_logger.write_api_call(False, "get_query_document_ids", str(request))
        return JsonResponse(status=500, data=dict(answer="Query not valid", reason=query_trans_string))

    if QueryTranslation.count_variables_in_query(graph_query) != 0:
        View().query_logger.write_api_call(False, "get_query_document_ids", str(request))
        return JsonResponse(status=500, data=dict(answer="Does not support queries with variables"))

    try:
        time_start = datetime.now()
        # compute the query
        results, _, _ = do_query_processing_with_caching(graph_query, {document_collection})
        result_ids = sorted(list({r.document_id for r in results}))
        View().query_logger.write_api_call(True, "get_query_document_ids", str(request),
                                           time_needed=datetime.now() - time_start)
        return JsonResponse(dict(results=result_ids))
    except Exception:
        View().query_logger.write_api_call(False, "get_query_document_ids", str(request))
        return JsonResponse(status=500, data=dict(answer="Internal server error"))


@gzip_page
def get_narrative_documents(request):
    if "document" not in request.GET and "documents" not in request.GET:
        View().query_logger.write_api_call(False, "get_narrative_document", str(request))
        return JsonResponse(status=500, data=dict(reason="document/documents parameter is missing"))
    if "data_source" not in request.GET:
        View().query_logger.write_api_call(False, "get_narrative_document", str(request))
        return JsonResponse(status=500, data=dict(reason="data_source parameter is missing"))

    document_ids = set()
    if "document" in request.GET:
        try:
            document_id = int(request.GET["document"].strip())
            document_ids.add(document_id)
        except ValueError:
            View().query_logger.write_api_call(False, "get_narrative_document", str(request))
            return JsonResponse(status=500, data=dict(reason="document must be an integer"))
    elif "documents" in request.GET:
        try:
            document_ids.update([int(did) for did in request.GET["documents"].strip().split(';')])
        except ValueError:
            View().query_logger.write_api_call(False, "get_narrative_document", str(request))
            return JsonResponse(status=500, data=dict(reason="documents must be a list of integer (separated by ;)"))

    document_collection = str(request.GET["data_source"]).strip()
    try:
        time_start = datetime.now()
        # get narrative documents
        session = SessionExtended.get()
        narrative_documents = retrieve_narrative_documents_from_database(session, document_ids=document_ids,
                                                                         document_collection=document_collection)

        View().query_logger.write_api_call(True, "get_narrative_document", str(request),
                                           time_needed=datetime.now() - time_start)
        return JsonResponse(dict(results=list([nd.to_dict() for nd in narrative_documents])))
    except Exception as e:
        logger.error(f"get_narrative_document: {e}")
        traceback.print_exc()
        View().query_logger.write_api_call(False, "get_narrative_document", str(request))
        return JsonResponse(status=500, data=dict(answer="Internal server error"))


def get_query_sub_count_with_caching(graph_query: GraphQuery, document_collection: str):
    """
    Does the query sub count processing with caching if activated
    :param graph_query: a graph query object
    :param document_collection: the document collection
    :return: a sub count list
    """
    aggregation_strategy = "overview"
    cached_sub_count_list = None
    if DO_CACHING:
        try:
            cached_sub_count_list = View().cache.load_result_from_cache(document_collection, graph_query,
                                                                        aggregation_name=aggregation_strategy)
            if cached_sub_count_list:
                logging.info('Sub Count cache hit - {} results loaded'.format(len(cached_sub_count_list)))
                return cached_sub_count_list, True
            else:
                cached_sub_count_list = None
        except Exception:
            logging.error('Cannot load query result from cache...')
    if not cached_sub_count_list:
        # run query
        # compute the query and do not load metadata (not required)
        results = QueryEngine.process_query_with_expansion(graph_query,
                                                           document_collection_filter={document_collection},
                                                           load_document_metadata=False)

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

        if DO_CACHING:
            try:
                View().cache.add_result_to_cache(document_collection, graph_query,
                                                 sub_count_list,
                                                 aggregation_name=aggregation_strategy)
            except Exception:
                logging.error('Cannot store query result to cache...')

        return sub_count_list, False


@gzip_page
def get_query_sub_count(request):
    if "query" in request.GET and "data_source" in request.GET:
        query = str(request.GET["query"]).strip()
        document_collection = str(request.GET["data_source"]).strip()
        if document_collection not in ["LitCovid", "LongCovid", "PubMed"]:
            return JsonResponse(status=500,
                                data=dict(answer="data source not valid", reason="Data sources supported: PubMed,"
                                                                                 " LitCovid and LongCovid"))

        graph_query, query_trans_string = View().translation.convert_query_text_to_fact_patterns(query)
        if not graph_query or len(graph_query.fact_patterns) == 0:
            View().query_logger.write_api_call(False, "get_query_sub_count", str(request))
            return JsonResponse(status=500, data=dict(answer="Query not valid", reason=query_trans_string))

        if QueryTranslation.count_variables_in_query(graph_query) != 1:
            View().query_logger.write_api_call(False, "get_query_sub_count", str(request))
            return JsonResponse(status=500, data=dict(answer="query must have one variable"))

        time_start = datetime.now()
        # Get sub count list via caching
        sub_count_list, cache_hit = get_query_sub_count_with_caching(graph_query, document_collection)

        if "topk" in request.GET:
            try:
                topk = int(str(request.GET["topk"]).strip())
                if topk <= 0:
                    return JsonResponse(status=500, data=dict(answer="topk must be a positive integer"))

                sub_count_list = sub_count_list[:topk]

            except ValueError:
                return JsonResponse(status=500, data=dict(answer="topk must be a positive integer"))

        View().query_logger.write_api_call(True, "get_query_sub_count", str(request),
                                           time_needed=datetime.now() - time_start)
        # send results back
        return JsonResponse(dict(sub_count_list=sub_count_list))
    else:
        View().query_logger.write_api_call(False, "get_query_sub_count", str(request))
        return HttpResponse(status=500)


def get_document_ids_for_entity(request):
    if "entity_id" not in request.GET or "entity_type" not in request.GET:
        View().query_logger.write_api_call(False, "get_document_ids_for_entity", str(request))
        return JsonResponse(status=500, data=dict(reason="entity_id and entity_type are required parameters"))
    if "data_source" not in request.GET:
        View().query_logger.write_api_call(False, "get_document_ids_for_entity", str(request))
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
        View().query_logger.write_api_call(True, "get_document_ids_for_entity", str(request),
                                           time_needed=datetime.now() - time_start)
        # send results back
        return JsonResponse(dict(document_ids=document_ids))

    except Exception as e:
        logger.error(f"get_document_ids_for_entity: {e}")
        traceback.print_exc()
        View().query_logger.write_api_call(False, "get_document_ids_for_entity", str(request))
        return JsonResponse(status=500, data=dict(answer="Internal server error"))


def get_document_collections_from_data_source_string(data_source: str) -> [str]:
    return set(data_source.split(";"))


# invokes Django to compress the results
@gzip_page
def get_query(request):
    results_converted = []
    is_aggregate = False
    valid_query = False
    query_limit_hit = False
    query_trans_string = ""
    if "query" not in request.GET:
        View().query_logger.write_api_call(False, "get_query", str(request))
        return JsonResponse(status=500, data=dict(reason="query parameter is missing"))
    if "data_source" not in request.GET:
        View().query_logger.write_api_call(False, "get_query", str(request))
        return JsonResponse(status=500, data=dict(reason="data_source parameter is missing"))

    try:
        query = str(request.GET.get("query", "").strip())
        data_source_str = str(request.GET.get("data_source", "").strip())
        document_collections = get_document_collections_from_data_source_string(data_source_str)
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

        year_start = None
        if "year_start" in request.GET:
            year_start = str(request.GET.get("year_start", "").strip())
            try:
                year_start = int(year_start)
            except ValueError:
                year_start = None

        year_end = None
        if "year_end" in request.GET:
            year_end = str(request.GET.get("year_end", "").strip())
            try:
                year_end = int(year_end)
            except ValueError:
                year_end = None

        title_filter = None
        if "title_filter" in request.GET:
            title_filter = str(request.GET.get("title_filter", "").strip())

        classification_filter = None
        if "classification_filter" in request.GET:
            classification_filter = str(request.GET.get("classification_filter", "").strip())
            if classification_filter:
                classification_filter = classification_filter.split(';')
            else:
                classification_filter = None

        # inner_ranking = str(request.GET.get("inner_ranking", "").strip())
        logging.info(f'Query string is: {query}')
        logging.info("Selected data source is {}".format(document_collections))
        logging.info('Strategy for outer ranking: {}'.format(outer_ranking))
        # logging.info('Strategy for inner ranking: {}'.format(inner_ranking))
        time_start = datetime.now()
        graph_query, query_trans_string = View().translation.convert_query_text_to_fact_patterns(
            query)
        year_aggregation = {}

        if not all(ds in DataSourcesFilter.get_available_db_collections() for ds in document_collections):
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

            results, cache_hit, time_needed = do_query_processing_with_caching(graph_query, document_collections)
            result_ids = {r.document_id for r in results}
            opt_query = QueryOptimizer.optimize_query(graph_query)
            View().query_logger.write_query_log(time_needed, "-".join(sorted(document_collections)), cache_hit,
                                                len(result_ids),
                                                query, opt_query)

            results = TitleFilter.filter_documents(results, title_filter)

            if classification_filter:
                logging.debug(f'Filtering document classifications with {classification_filter}...')
                results = ClassificationFilter.filter_documents(results, document_classes=classification_filter)

            year_aggregation = TimeFilter.aggregate_years(results)
            results = TimeFilter.filter_documents_by_year(results, year_start, year_end)

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

        View().query_logger.write_api_call(True, "get_query", str(request),
                                           time_needed=datetime.now() - time_start)

        return JsonResponse(
            dict(valid_query=valid_query, is_aggregate=is_aggregate, results=results_converted,
                 query_translation=query_trans_string, year_aggregation=year_aggregation,
                 query_limit_hit="False"))
    except Exception:
        View().query_logger.write_api_call(False, "get_query", str(request))
        query_trans_string = "keyword query cannot be converted (syntax error)"
        traceback.print_exc(file=sys.stdout)
        return JsonResponse(
            dict(valid_query="", results=[], query_translation=query_trans_string, year_aggregation="",
                 query_limit_hit="False"))


def get_provenance(request):
    if "prov" in request.GET and "document_id" in request.GET and "data_source" in request.GET:
        try:
            document_id = str(request.GET["document_id"]).strip()
            document_collection = str(request.GET["data_source"]).strip()
            start = datetime.now()
            fp2prov_ids = json.loads(str(request.GET.get("prov", "").strip()))
            result = QueryEngine.query_provenance_information(fp2prov_ids)
            time_needed = datetime.now() - start
            predication_ids = set()
            for _, pred_ids in fp2prov_ids.items():
                predication_ids.update(pred_ids)
            try:
                View().query_logger.write_provenance_log(time_needed, document_collection, document_id,
                                                         predication_ids)
            except IOError:
                logging.debug('Could not write provenance log file')

            View().query_logger.write_api_call(True, "get_provenance", str(request),
                                               time_needed=datetime.now() - start)
            return JsonResponse(dict(result=result.to_dict()))
        except Exception:
            View().query_logger.write_api_call(False, "get_provenance", str(request))
            traceback.print_exc(file=sys.stdout)
            return HttpResponse(status=500)
    else:
        View().query_logger.write_api_call(False, "get_provenance", str(request))
        return HttpResponse(status=500)


def get_explain_document(request):
    required_parameters = {"document_id", "query", "document_collection"}
    try:
        if not required_parameters.issubset(request.GET.keys()):
            View().query_logger.write_api_call(False, "get_explain_document", str(request))
            return HttpResponse(status=500)
        start = datetime.now()

        document_id = str(request.GET.get("document_id", "")).strip()
        document_collection = str(request.GET.get("document_collection", "")).strip()
        query = str(request.GET.get("query", "").strip())
        variables = ""
        if "variables" in request.GET:
            variables = request.GET.get("variables", "")

        graph_query, query_trans_string = View().translation.convert_query_text_to_fact_patterns(query)
        result = QueryEngine.explain_document(document_id, document_collection, graph_query,
                                              variables)
        View().query_logger.write_api_call(True, "get_explain_document", str(request), start - datetime.now())
        return JsonResponse(dict(result=result.to_dict()))

    except Exception:
        View().query_logger.write_api_call(False, "get_explain_document", str(request))
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
            predication_ids = list([int(d) for d in data["predicationids"].split(',')])
            query_str = data["query"]
            rating = data["rating"]
            userid = data["userid"]

            # we need to find the predication info and sentence info that belongs
            # to this user rating. Both information must be queried from DB
            session = SessionExtended.get()
            db_query = session.query(Predication, Sentence)
            db_query = db_query.filter(Predication.id.in_(predication_ids))
            db_query = db_query.filter(Sentence.id == Predication.sentence_id)
            result = []
            for res in db_query:
                result.append(dict(document_id=res.Predication.document_id,
                                   document_collection=res.Predication.document_collection,
                                   rating=rating,
                                   user_id=userid,
                                   query=query_str,
                                   subject_id=res.Predication.subject_id,
                                   subject_type=res.Predication.subject_type,
                                   subject_str=res.Predication.subject_str,
                                   predicate=res.Predication.predicate,
                                   relation=res.Predication.relation,
                                   object_id=res.Predication.object_id,
                                   object_type=res.Predication.object_type,
                                   object_str=res.Predication.object_str,
                                   sentence=res.Sentence.text))

            # create a filename for this rating
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            rating_filename = os.path.join(FEEDBACK_PREDICATION_DIR, f'predication_{userid}_{timestamp}.json')
            with open(rating_filename, 'wt') as f:
                json.dump(result, f, sort_keys=True, indent=4)

            logging.info(f'User "{userid}" has rated "{predication_ids}" as "{rating} (stored in {rating_filename})"')
            try:
                View().query_logger.write_rating(query_str, userid, predication_ids)
            except IOError:
                logging.debug('Could not write rating log file')
            View().query_logger.write_api_call(True, "get_feedback", str(request),
                                               time_needed=datetime.now() - time_start)
            return HttpResponse(status=200)
        except Exception:
            View().query_logger.write_api_call(False, "get_feedback", str(request))
            traceback.print_exc(file=sys.stdout)
            return HttpResponse(status=500)
    View().query_logger.write_api_call(False, "get_feedback", str(request))
    return HttpResponse(status=500)


def post_document_classification_feedback(request):
    try:
        data = json.loads(request.body)
    except JSONDecodeError:
        logging.debug('Invalid JSON received')
        View().query_logger.write_api_call(False, "post_document_classification_feedback", str(request))
        return HttpResponse(status=500)

    if data and data.keys() & {"doc_id", "doc_collection", "classification", "rating", "user_id"}:
        try:
            time_start = datetime.now()
            userid = data["user_id"]

            result = {
                "document_id": data["doc_id"],
                "document_collection": data["doc_collection"],
                "document_classification": data["classification"],
                "rating": data["rating"],
                "user_id": userid,
            }

            # create a filename for this rating
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            rating_filename = os.path.join(FEEDBACK_CLASSIFICATION, f'classification_{userid}_{timestamp}.json')
            with open(rating_filename, 'wt') as f:
                json.dump(result, f, sort_keys=True, indent=4)

            View().query_logger.write_api_call(True, "post_document_classification_feedback", str(request),
                                               time_needed=datetime.now() - time_start)
            return HttpResponse(status=200)
        except Exception:
            View().query_logger.write_api_call(False, "post_document_classification_feedback", str(request))
            traceback.print_exc(file=sys.stdout)
            return HttpResponse(status=500)
    View().query_logger.write_api_call(False, "post_document_classification_feedback", str(request))
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

            result = dict(variable_name=variable_name,
                          entity_name=entity_name,
                          entity_id=entity_id,
                          entity_type=entity_type,
                          query=query,
                          user_id=userid,
                          rating=rating)

            # create a filename for this rating
            timestamp = datetime.now().strftime("%Y-%d-%d_%H-%M-%S")
            rating_filename = os.path.join(FEEDBACK_SUBGROUP_DIR, f'subgroup_{userid}_{timestamp}.json')
            with open(rating_filename, 'wt') as f:
                json.dump(result, f, sort_keys=True, indent=4)

            logging.info(f'User "{userid}" has rated "{variable_name}":'
                         f'[{entity_name}, {entity_id}, {entity_type}] as "{rating}"')
            try:
                View().query_logger.write_subgroup_rating_log(
                    query, userid, variable_name, entity_name, entity_id, entity_type)
            except IOError:
                logging.debug('Could not write rating log file')
            View().query_logger.write_api_call(True, "get_subgroup_feedback", str(request),
                                               time_needed=datetime.now() - time_start)
            return HttpResponse(status=200)
        except Exception:
            View().query_logger.write_api_call(False, "get_subgroup_feedback", str(request))
            traceback.print_exc(file=sys.stdout)
            return HttpResponse(status=500)

    View().query_logger.write_api_call(False, "get_subgroup_feedback", str(request))
    return HttpResponse(status=500)


def post_drug_suggestion(request):
    data = None
    try:
        data = json.loads(request.body)
    except JSONDecodeError:
        logging.debug('Invalid JSON received')
        return HttpResponse(status=500)

    if data and data.keys() & {"drug", "description"}:
        try:
            time_start = datetime.now()
            drug = data["drug"]
            description = data["description"]

            logging.info(f'received new drug suggestion {drug}')
            try:
                View().query_logger.write_drug_suggestion(drug, description)
            except IOError:
                logging.debug('Could not write drug suggestion log file')
            View().query_logger.write_api_call(True, "post_drug_suggestion", str(request),
                                               time_needed=datetime.now() - time_start)
            return HttpResponse(status=200)

        except IOError:
            View().query_logger.write_api_call(False, "post_drug_suggestion", str(request))
            traceback.print_exc(file=sys.stdout)
            return HttpResponse(status=500)

    View().query_logger.write_api_call(False, "post_drug_suggestion", str(request))
    return HttpResponse(status=500)


def post_document_link_clicked(request):
    data = None
    try:
        data = json.loads(request.body)
    except JSONDecodeError:
        logging.debug('Invalid JSON received')
        View().query_logger.write_api_call(False, "document_clicked", str(request))
        return HttpResponse(status=500)

    if data and data.keys() & {"query", "document_id", "link", "data_source"}:
        query = data["query"]
        document_id = data["document_id"]
        document_collection = data["data_source"]
        link = data["link"]
        try:
            View().query_logger.write_document_link_clicked(query, document_collection, document_id, link)
        except IOError:
            View().query_logger.write_api_call(False, "document_clicked", str(request))
            return HttpResponse(status=500)
        View().query_logger.write_api_call(True, "document_clicked", str(request))
        return HttpResponse(status=200)
    View().query_logger.write_api_call(False, "document_clicked", str(request))
    return HttpResponse(status=500)


def post_paper_view_log(request):
    data = None
    try:
        data = json.loads(request.body)
    except JSONDecodeError:
        View().query_logger.write_api_call(False, "paper_view_log", str(request))
        return HttpResponse(status=500)

    if data and data.keys() & {"doc_id", "doc_collection"}:
        doc_id = data["doc_id"]
        doc_collection = data["doc_collection"]

        try:
            View().query_logger.write_paper_view(doc_id, doc_collection)
        except IOError:
            View().query_logger.write_api_call(False, "paper_view_log", str(request))
            return HttpResponse(status=500)

        View().query_logger.write_api_call(True, "paper_view_log", str(request))
        return HttpResponse(status=200)
    View().query_logger.write_api_call(False, "paper_view_log", str(request))
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
            View().query_logger.write_drug_ov_search(drug)
        except IOError:
            logging.debug('Could not write drug searched log file')
        return HttpResponse(status=200)
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
            View().query_logger.write_drug_ov_substance_href(drug, substance, query)
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
            View().query_logger.write_drug_ov_chembl_phase_href(drug, disease_name, disease_id, phase, query)
        except IOError:
            logging.debug('Could not write chembl phase href log file')
        return HttpResponse(status=200)
    return HttpResponse(status=500)


def post_report(request):
    try:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except JSONDecodeError:
            logging.debug('Invalid JSON received')
            return HttpResponse(status=500)
        req_data = json.loads(request.body.decode("utf-8"))
        report_description = req_data.get("description", "")
        report_img_64 = req_data.get("img64", "")
        report_path = os.path.join(FEEDBACK_REPORT_DIR, f"{datetime.now():%Y-%m-%d_%H-%M-%S}")
        os.makedirs(report_path, exist_ok=True)
        with open(os.path.join(report_path, "description.txt"), "w+") as f:
            f.write(report_description)

        with open(os.path.join(report_path, "screenshot.png"), "wb") as f:
            f.write(base64.b64decode(report_img_64[22:]))
        return HttpResponse(status=200)

    except:
        traceback.print_exc(file=sys.stdout)
        return HttpResponse(status=500)


def get_keywords(request):
    if request.GET.keys() & {"substance_id"}:
        substance_id = request.GET.get("substance_id", "")
        if substance_id.strip():
            try:
                session = SessionExtended.get()
                query = session.query(EntityKeywords.keyword_data).filter(EntityKeywords.entity_id == substance_id)
                try:
                    result = query.first()

                    keywords = ""
                    if result:
                        keywords = ast.literal_eval(result[0])
                except OperationalError:
                    pass

                return JsonResponse(dict(keywords=keywords))

            except Exception:
                logging.debug(f"Could not retrieve keywords for {substance_id}")
    return HttpResponse(status=500)


def get_explain_translation(request):
    if "concept" in request.GET and 'query' in request.GET:
        try:
            concept = str(request.GET["concept"]).strip()
            search_string = str(request.GET.get("query", "").strip())
            logging.info(f'checking query: {search_string}')
            query_fact_patterns, query_trans_string = View().translation.convert_query_text_to_fact_patterns(
                search_string)

            if not query_fact_patterns:
                return JsonResponse(dict(headings=["Please complete query first"]))

            # If the search string starts with the concepts
            # However, composed words like "Mass Spectrometry" starts with a quote character
            # So ignore all quote characters here
            search_string = search_string.replace('"', '').strip()
            concept_string = concept.replace('"', '').strip()
            if search_string.startswith(concept_string):
                entities = query_fact_patterns.fact_patterns[0].subjects
            else:
                entities = query_fact_patterns.fact_patterns[0].objects

            headings = View.explainer.explain_entities(entities)
            return JsonResponse(dict(headings=headings))
        except KeyError:
            return JsonResponse(dict(headings=["Not known yet"]))
        except Exception:
            View().query_logger.write_api_call(False, "get_explain_translation", str(request))
            traceback.print_exc(file=sys.stdout)
            return HttpResponse(status=500)
    else:
        View().query_logger.write_api_call(False, "get_explain_translation", str(request))
        return HttpResponse(status=500)


def get_last_db_update(request):
    try:
        session = SessionExtended.get()
        last_update = str(DatabaseUpdate.get_latest_update(session))
        last_update = last_update.replace('-', '.')
        logging.debug(f"Get last DB update: {last_update}")
        View().query_logger.write_api_call(True, "get_last_db_update", str(request))
        return JsonResponse(data=dict(last_update=last_update))
    except Exception as e:
        View().query_logger.write_api_call(False, "get_last_db_update", str(request))
        traceback.print_exc(file=sys.stdout)
        return HttpResponse(status=500)


class SearchView(TemplateView):
    template_name = "ui/search.html"

    def __init__(self):
        init_view = View()
        super(SearchView, self).__init__()

    def get(self, request, *args, **kwargs):
        View().query_logger.write_page_view_log(SearchView.template_name)
        return super().get(request, *args, **kwargs)


class SwaggerUIView(TemplateView):
    template_name = "ui/swagger-ui.html"


class LogsView(TemplateView):
    template_name = "ui/logs.html"
    log_date = None
    data_dict = None

    @staticmethod
    def recompute_logs_if_necessary():
        if not LogsView.log_date or (datetime.now() - LogsView.log_date).seconds > 3600 or not LogsView.data_dict:
            try:
                logger.debug("Computing logs")
                log_path = os.path.join(LOG_DIR, "daily_logs_cache")
                today = datetime.now().date()
                cache_filename = f"daily_logs_cache_{today.strftime('%Y%m%d')}.json"
                cache_file_path = os.path.join(log_path, cache_filename)
                if os.path.exists(cache_file_path):
                    try:
                        with open(cache_file_path, 'r') as cache_file:
                            data = json.load(cache_file)
                    except json.JSONDecodeError:
                        logger.error("Error decoding JSON from the cache file.")
                    except IOError as e:
                        logger.error(f"Error reading the cache file: {e}")
                else:
                    logger.warning(f"No cache file found for today: {cache_file_path}")

                LogsView.data_dict = data
                LogsView.log_date = datetime.now()
                logger.debug("Logs computed")
            except:
                traceback.print_exc(file=sys.stdout)

    def get(self, request, *args, **kwargs):
        View().query_logger.write_page_view_log(LogsView.template_name)
        LogsView.recompute_logs_if_necessary()
        return super().get(request, *args, **kwargs)


def get_logs_data(request):
    LogsView.recompute_logs_if_necessary()
    return JsonResponse(LogsView.data_dict)


class StatsView(TemplateView):
    template_name = "ui/stats.html"
    stats_query_results = None

    def get(self, request, *args, **kwargs):
        View().query_logger.write_page_view_log(StatsView.template_name)
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
        View().query_logger.write_page_view_log(HelpView.template_name)
        return super().get(request, *args, **kwargs)


class DocumentView(TemplateView):
    template_name = "ui/paper.html"

    def get(self, request, *args, **kwargs):
        View().query_logger.write_page_view_log(DocumentView.template_name)
        return super().get(request, *args, **kwargs)


class DrugOverviewView(TemplateView):
    template_name = "ui/drug_overview.html"

    def get(self, request, *args, **kwargs):
        View().query_logger.write_page_view_log(DrugOverviewView.template_name)
        return super().get(request, *args, **kwargs)


class LongCovidView(TemplateView):
    template_name = "ui/long_covid.html"

    def get(self, request, *args, **kwargs):
        View().query_logger.write_page_view_log(LongCovidView.template_name)
        return super().get(request, *args, **kwargs)


class CovidView19(TemplateView):
    template_name = "ui/covid19.html"

    def get(self, request, *args, **kwargs):
        View().query_logger.write_page_view_log(CovidView19.template_name)
        return super().get(request, *args, **kwargs)


class MECFSView(TemplateView):
    template_name = "ui/mecfs.html"

    def get(self, request, *args, **kwargs):
        View().query_logger.write_page_view_log(MECFSView.template_name)
        return super().get(request, *args, **kwargs)


def get_keyword_search_request(request):
    if request.GET.keys() & {"keywords"}:
        keywords = request.GET.get("keywords", "")
        if keywords.strip():
            time_start = datetime.now()
            try:
                logging.debug('Generating graph queries for "{}"'.format(keywords))

                keywords = keywords.split("_AND_")
                if len(keywords) < 2:
                    return JsonResponse(status=500, data=dict(reason="At least two keywords are required."))

                possible_queries = View().keyword2graph.translate_keywords(keywords)
                json_data = [r.to_json_data() for r in possible_queries]
                # This is the format
                # json_data = [
                #     [("Metformin", "treats", "Diabetes Mellitus")],
                #     [("Metformin", "treats", "Diabetes Mellitus"), ("Metformin", "administered", "Syringe")],
                #     [("Insulin", "associated", "Diabetes Mellitus")],
                # ]

                View().query_logger.write_api_call(True, "get_keyword_search_request", str(request),
                                                   time_needed=datetime.now() - time_start)
                return JsonResponse(status=200, data=dict(query_graphs=json_data))

            except Exception as e:
                View().query_logger.write_api_call(False, "get_keyword_search_request", str(request),
                                                   time_needed=datetime.now() - time_start)
                query_trans_string = str(e)
                logging.debug(f'Could not generate graph queries for "{keywords}: {e}"')
                return JsonResponse(status=500, data=dict(reason=query_trans_string))

    return HttpResponse(status=500)


logging.info('Initialize view')
View()


def get_clinical_trial_phases(request):
    if request.GET.keys() & {"molecule_chembl_id"}:
        chembl_id = request.GET.get("molecule_chembl_id", "")

        if not chembl_id.strip():
            logging.debug('Could not query clinical trials for empty chembl id')
            return HttpResponse(status=500)

        time_start = datetime.now()
        session = SessionExtended.get()
        try:
            q = session.query(DrugDiseaseTrialPhase)
            q = q.filter(DrugDiseaseTrialPhase.drug == chembl_id)

            drug_indications = []

            for row in q:
                drug_indications.append(dict(mesh_id=row.disease, max_phase_for_ind=row.phase))

            View().query_logger.write_api_call(True, "clinical_trial_phases", str(request),
                                               time_needed=datetime.now() - time_start)
            return JsonResponse(status=200, data=dict(drug_indications=drug_indications))
        except Exception as _:
            logging.debug('Could not query clinical trials for {}'.format(chembl_id))
            View().query_logger.write_api_call(False, "clinical_trial_phases", str(request),
                                               time_needed=datetime.now() - time_start)

            return HttpResponse(status=500)
    return HttpResponse(status=500)


def get_data_sources(request):
    try:
        available_data_sources = DataSourcesFilter.get_available_data_sources()
        return JsonResponse(status=200, data=dict(data_sources=available_data_sources))
    except Exception:
        return HttpResponse(status=500)


def get_classifications(request):
    try:
        available_classifications = ClassificationFilter.get_available_classifications()
        return JsonResponse(status=200, data=dict(classifications=available_classifications))
    except Exception:
        return HttpResponse(status=500)


def get_recommend(request):
    results_converted = []
    is_aggregate = False
    valid_query = False
    query_trans_string = ""
    if "query" not in request.GET:
        View().query_logger.write_api_call(False, "get_query", str(request))
        return JsonResponse(status=500, data=dict(reason="document_id parameter is missing"))
    if "query_col" not in request.GET:
        View().query_logger.write_api_call(False, "get_query", str(request))
        return JsonResponse(status=500, data=dict(reason="document_collection parameter is missing"))
    if "data_source" not in request.GET:
        View().query_logger.write_api_call(False, "get_query", str(request))
        return JsonResponse(status=500, data=dict(reason="data_source parameter is missing"))
    try:
        if not request.GET.keys():
            return HttpResponse(status=500)

        document_id = int(request.GET.get("query", ""))
        query_collection = request.GET.get("query_col", "")
        query_trans_string = document_id
        document_collections = request.GET.get("data_source", "")

        if "outer_ranking" in request.GET:
            outer_ranking = str(request.GET.get("outer_ranking", "").strip())
        else:
            outer_ranking = "outer_ranking_substitution"

        year_start = None
        if "year_start" in request.GET:
            year_start = str(request.GET.get("year_start", "").strip())
            try:
                year_start = int(year_start)
            except ValueError:
                year_start = None

        year_end = None
        if "year_end" in request.GET:
            year_end = str(request.GET.get("year_end", "").strip())
            try:
                year_end = int(year_end)
            except ValueError:
                year_end = None

        title_filter = None
        if "title_filter" in request.GET:
            title_filter = str(request.GET.get("title_filter", "").strip())

        classification_filter = None
        if "classification_filter" in request.GET:
            classification_filter = str(request.GET.get("classification_filter", "").strip())
            if classification_filter:
                classification_filter = classification_filter.split(';')
            else:
                classification_filter = None

        logging.info("Selected data source is {}".format(document_collections))
        logging.info('Strategy for outer ranking: {}'.format(outer_ranking))
        time_start = datetime.now()
        year_aggregation = {}
        document_collections = set(document_collections.split(";"))
        if not all(ds in DataSourcesFilter.get_available_db_collections() for ds in document_collections):
            results_converted = []
            query_trans_string = "Data source is unknown"
            logger.error('parsing error')
        elif outer_ranking not in ["outer_ranking_substitution", "outer_ranking_ontology"]:
            query_trans_string = "Outer ranking strategy is unknown"
            logger.error('parsing error')
        else:
            valid_query = True
            logging.debug(f'Performing paper recommendation for document id {document_id}, '
                          f'query collection {query_collection} and document collections {document_collections}')

            json_data = View().recommender.apply_recommendation(document_id, query_collection, document_collections)

            results = []
            graph_data = dict()
            for d in json_data:
                results.append(QueryDocumentResult(document_id=d["docid"],
                                                   title=d["title"],
                                                   authors=d["authors"],
                                                   journals=d["journals"],
                                                   publication_year=d["year"],
                                                   publication_month=d["month"],
                                                   var2substitution={},
                                                   confidence=1.0,
                                                   position2provenance_ids={},
                                                   org_document_id=d["org_document_id"],
                                                   doi=d["doi"],
                                                   document_collection=d["collection"]))
                graph_data[d["docid"]] = d["graph_data"]

            # do filtering stuff
            year_aggregation = TimeFilter.aggregate_years(results)
            results = TimeFilter.filter_documents_by_year(results, year_start, year_end)
            results = TitleFilter.filter_documents(results, title_filter)
            if classification_filter:
                logging.debug(f'Filtering document classifications with {classification_filter}...')
                results = ClassificationFilter.filter_documents(results, document_classes=classification_filter)

            result_list = QueryDocumentResultList()
            for r in results:
                result_list.add_query_result(r)

            results_converted = result_list.to_dict()
            for idx, entry in enumerate(results_converted["r"]):
                entry["graph_data"] = graph_data[entry["docid"]]

        View().query_logger.write_api_call(True, "get_recommendation", str(request),
                                           time_needed=datetime.now() - time_start)

        return JsonResponse(dict(valid_query=valid_query, is_aggregate=is_aggregate, results=results_converted,
                                 query_translation=query_trans_string, year_aggregation=year_aggregation,
                                 query_limit_hit="False"))


    except Exception:
        View().query_logger.write_api_call(False, "get_recommend", str(request))
        error_msg = "recommendation can not be applied"
        traceback.print_exc(file=sys.stdout)
        return JsonResponse(
            dict(valid_query="", results=[], query_translation=error_msg, year_aggregation="",
                 query_limit_hit="False"))
