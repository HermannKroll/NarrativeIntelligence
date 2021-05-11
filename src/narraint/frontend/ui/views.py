import logging
import re
import traceback
import sys
from typing import List

from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.views.generic import TemplateView
from sqlalchemy import func

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication
from narraint.frontend.entity.query_translation import QueryTranslation
from narrant.entity.entityresolver import EntityResolver
from narraint.frontend.entity.entitytagger import EntityTagger
from narraint.queryengine.aggregation.ontology import ResultAggregationByOntology
from narraint.queryengine.aggregation.substitution import ResultAggregationBySubstitution
from narraint.queryengine.engine import QueryEngine
from narraint.queryengine.query import GraphQuery
from narraint.frontend.ui.search_cache import SearchCache
from narraint.frontend.entity.autocompletion import AutocompletionUtil


logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)



class View:
    """
    Singleton encapsulating the former global query_engine, entity_tagger and cache
    """
    query_engine = None
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
            cls.resolver = EntityResolver.instance()
            cls.query_engine = QueryEngine()
            cls.entity_tagger = EntityTagger.instance()
            cls.cache = SearchCache()
            cls.autocompletion = AutocompletionUtil.instance()
            cls.translation = QueryTranslation()
        return cls._instance




@sync_to_async
def sync_autocompletion(search_string: str) -> List[str]:
    return View.instance().autocompletion.compute_autocompletion_list(search_string)


async def get_autocompletion(request):
    completion_terms = []
    if "term" in request.GET:
        search_string = str(request.GET.get("term", "").strip())
        completion_terms = await sync_to_async(sync_autocompletion, thread_sensitive=False)(search_string)
        logging.info(f'For {search_string} sending completion terms: {completion_terms}')
    return JsonResponse(dict(terms=completion_terms))


@sync_to_async
def sync_convert_query(search_string: str) -> (GraphQuery, str):
    return View.instance().translation.convert_query_text_to_fact_patterns(search_string)


async def get_check_query(request):
    if "query" in request.GET:
        search_string = str(request.GET.get("query", "").strip())
        logging.info(f'checking query: {search_string}')
        query_fact_patterns, query_trans_string = await sync_to_async(sync_convert_query, thread_sensitive=False)(search_string)
        if query_fact_patterns:
            logging.info('query is valid')
            return JsonResponse(dict(valid="True"))
        else:
            logging.info(f'query is not valid: {query_trans_string}')
            return JsonResponse(dict(valid=query_trans_string))
    return JsonResponse(dict(valid="False"))

@sync_to_async
def sync_process_query(request):
    results_converted = []
    valid_query = False
    query_limit_hit = False
    query_trans_string = ""
    try:
        query = str(request.GET.get("query", "").strip())
        data_source = str(request.GET.get("data_source", "").strip())
        outer_ranking = str(request.GET.get("outer_ranking", "").strip())
        # inner_ranking = str(request.GET.get("inner_ranking", "").strip())
        logging.info(f'Query string is: {query}')
        logging.info("Selected data source is {}".format(data_source))
        logging.info('Strategy for outer ranking: {}'.format(outer_ranking))
        # logging.info('Strategy for inner ranking: {}'.format(inner_ranking))

        query_fact_patterns, query_trans_string = View.instance().translation.convert_query_text_to_fact_patterns(query)
        if data_source not in ["PMC", "PubMed"]:
            results_converted = []
            query_trans_string = "Data source is unknown"
            logger.error('parsing error')
        elif outer_ranking not in ["outer_ranking_substitution", "outer_ranking_ontology"]:
            query_trans_string = "Outer ranking strategy is unknown"
            logger.error('parsing error')
        elif not query_fact_patterns or len(query_fact_patterns.fact_patterns) == 0:
            results_converted = []
            logger.error('parsing error')
        elif outer_ranking == 'outer_ranking_ontology' and QueryTranslation.count_variables_in_query(
                query_fact_patterns) > 1:
            results_converted = []
            nt_string = ""
            query_trans_string = "Do not support multiple variables in an ontology-based ranking"
            logger.error("Do not support multiple variables in an ontology-based ranking")
        else:
            logger.info(f'Translated Query is: {str(query_fact_patterns)}')
            valid_query = True
            document_collection = data_source
            try:
                cached_results, query_limit_hit = View.instance().cache.load_result_from_cache(document_collection,
                                                                                               query_fact_patterns)
            except Exception:
                logging.error('Cannot load query result from cache...')
                cached_results = None
            if cached_results:
                logging.info('Cache hit - {} results loaded'.format(len(cached_results)))
                results = cached_results
            else:
                results, query_limit_hit = View.instance().query_engine.process_query_with_expansion(
                    query_fact_patterns, document_collection, query=query)
                try:
                    View.instance().cache.add_result_to_cache(document_collection, query_fact_patterns,
                                                              results, query_limit_hit)
                except Exception:
                    logging.error('Cannot store query result to cache...')
            results_converted = []
            if outer_ranking == 'outer_ranking_substitution':
                substitution_aggregation = ResultAggregationBySubstitution()
                results_converted = substitution_aggregation.rank_results(results).to_dict()
            elif outer_ranking == 'outer_ranking_ontology':
                substitution_ontology = ResultAggregationByOntology()
                results_converted = substitution_ontology.rank_results(results).to_dict()
            return valid_query, results_converted, query_trans_string, query_limit_hit
    except Exception:
        results_converted = []
        query_trans_string = "keyword query cannot be converted (syntax error)"
        traceback.print_exc(file=sys.stdout)
    return valid_query, results_converted, query_trans_string, query_limit_hit


async def get_query(request):
    if "query" in request.GET:
        valid_query, results_converted, query_trans_string, query_limit_hit = \
            await sync_to_async(sync_process_query, thread_sensitive=False)(request)
        return JsonResponse(
            dict(valid_query=valid_query, results=results_converted, query_translation=query_trans_string,
                 query_limit_hit=query_limit_hit))
    else:
        return JsonResponse(
            dict(valid_query="", results=[], query_translation="",
                 query_limit_hit="False"))


class SearchView(TemplateView):
    template_name = "ui/search.html"

    def __init__(self):
        init_view = View.instance()
        super(SearchView, self).__init__()

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class StatsView(TemplateView):
    template_name = "ui/stats.html"
    stats_query_results = None

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            if "query" in request.GET:
                if not StatsView.stats_query_results:
                    session = SessionExtended.get()
                    try:
                        logging.info('Processing database statistics...')
                        StatsView.stats_query_results = session.query(Predication.predicate_canonicalized,
                                                                      Predication.extraction_type,
                                                                      func.count(Predication.predicate_canonicalized)). \
                            group_by(Predication.predicate_canonicalized).group_by(Predication.extraction_type).all()
                    except:
                        traceback.print_exc(file=sys.stdout)
                    session.close()
                return JsonResponse(
                    dict(results=StatsView.stats_query_results)
                )
        return super().get(request, *args, **kwargs)
