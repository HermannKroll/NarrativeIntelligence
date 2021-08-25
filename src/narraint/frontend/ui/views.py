import base64
import json
import logging
import os
import traceback
import sys
from datetime import datetime
from io import BytesIO

from PIL import Image
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.gzip import gzip_page
from django.views.generic import TemplateView
from sqlalchemy import func

from narraint.backend.database import SessionExtended
from narraint.backend.models import Predication, PredicationRating
from narraint.config import REPORT_DIR
from narraint.frontend.entity.query_translation import QueryTranslation
from narraint.queryengine.logger import QueryLogger
from narraint.queryengine.optimizer import QueryOptimizer
from narrant.entity.entityresolver import EntityResolver
from narraint.frontend.entity.entitytagger import EntityTagger
from narraint.queryengine.aggregation.ontology import ResultAggregationByOntology
from narraint.queryengine.aggregation.substitution import ResultAggregationBySubstitution
from narraint.queryengine.engine import QueryEngine
from narraint.frontend.ui.search_cache import SearchCache
from narraint.frontend.entity.autocompletion import AutocompletionUtil

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)
DO_CACHING = False


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
            cls.resolver = EntityResolver.instance()
            cls.entity_tagger = EntityTagger.instance()
            cls.cache = SearchCache()
            cls.autocompletion = AutocompletionUtil.instance()
            cls.translation = QueryTranslation()
            cls.query_logger = QueryLogger()
        return cls._instance


def get_document_graph(request):
    if "document" in request.GET:
        document_id = str(request.GET.get("document", "").strip())
        try:
            document_id = int(document_id)
            session = SessionExtended.get()
            query = session.query(Predication).filter(Predication.document_collection == 'PubMed')
            query = query.filter(Predication.document_id == document_id)
            query = query.filter(Predication.relation.isnot(None))
            facts = set()
            nodes = set()
            for r in query:
                subject_name = View.instance().resolver.get_name_for_var_ent_id(r.subject_id, r.subject_type, resolve_gene_by_id=False)
                object_name = View.instance().resolver.get_name_for_var_ent_id(r.object_id, r.object_type, resolve_gene_by_id=False)
                subject_name = f'{subject_name} ({r.subject_type})'
                object_name = f'{object_name} ({r.object_type})'
                key = subject_name, r.relation, object_name
                facts.add(key)
                nodes.add(subject_name)
                nodes.add(object_name)

            result = []
            for s, p, o in facts:
                result.append(dict(s=s, p=p, o=o))
            logging.info(f'Querying document graph for document id: {document_id} - {len(facts)} facts found')
            return JsonResponse(dict(nodes=list(nodes), facts=result))
        except ValueError:
            return JsonResponse(dict(nodes=[], facts=[]))
    return JsonResponse(dict(nodes=[], facts=[]))


def get_autocompletion(request):
    completion_terms = []
    if "term" in request.GET:
        search_string = str(request.GET.get("term", "").strip())
        completion_terms = View.instance().autocompletion.compute_autocompletion_list(search_string)
        logging.info(f'For {search_string} sending completion terms: {completion_terms}')
    return JsonResponse(dict(terms=completion_terms))


def get_check_query(request):
    try:
        search_string = str(request.GET.get("query", "").strip())
        logging.info(f'checking query: {search_string}')
        query_fact_patterns, query_trans_string = View.instance().translation.convert_query_text_to_fact_patterns(
            search_string)
        if query_fact_patterns:
            logging.info('query is valid')
            return JsonResponse(dict(valid="True"))
        else:
            logging.info(f'query is not valid: {query_trans_string}')
            return JsonResponse(dict(valid=query_trans_string))
    except:
        return JsonResponse(dict(valid="False"))

# invokes Django to compress the results
@gzip_page
def get_query(request):
    results_converted = []
    valid_query = False
    query_limit_hit = False
    query_trans_string = ""
    try:
        query = str(request.GET.get("query", "").strip())
        data_source = str(request.GET.get("data_source", "").strip())
        outer_ranking = str(request.GET.get("outer_ranking", "").strip())
        freq_sort_desc = str(request.GET.get("freq_sort", "").strip())
        year_sort_desc = str(request.GET.get("year_sort", "").strip())
        end_pos = request.GET.get("end_pos").strip()
        if freq_sort_desc == 'False':
            freq_sort_desc = False
        else:
            freq_sort_desc = True
        if year_sort_desc == 'False':
            year_sort_desc = False
        else:
            year_sort_desc = True
        try:
            end_pos = int(end_pos)
        except:
            end_pos = None
        # inner_ranking = str(request.GET.get("inner_ranking", "").strip())
        logging.info(f'Query string is: {query}')
        logging.info("Selected data source is {}".format(data_source))
        logging.info('Strategy for outer ranking: {}'.format(outer_ranking))
        # logging.info('Strategy for inner ranking: {}'.format(inner_ranking))

        graph_query, query_trans_string = View.instance().translation.convert_query_text_to_fact_patterns(
            query)
        if data_source not in ["PMC", "PubMed"]:
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
            start_time = datetime.now()
            cached_results = None
            cache_hit = False
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
                results = QueryEngine.process_query_with_expansion(graph_query)
                cache_hit = False
                if DO_CACHING:
                    try:
                        View.instance().cache.add_result_to_cache(document_collection, graph_query, results)
                    except Exception:
                        logging.error('Cannot store query result to cache...')
            time_needed = datetime.now() - start_time
            result_ids = {r.document_id for r in results}
            opt_query = QueryOptimizer.optimize_query(graph_query)
            View.instance().query_logger.write_log(time_needed, document_collection, cache_hit, len(result_ids),
                                                   query, opt_query)
            results_converted = []
            if outer_ranking == 'outer_ranking_substitution':
                substitution_aggregation = ResultAggregationBySubstitution()
                results_converted = substitution_aggregation.rank_results(results, freq_sort_desc, year_sort_desc, end_pos).to_dict()
            elif outer_ranking == 'outer_ranking_ontology':
                substitution_ontology = ResultAggregationByOntology()
                results_converted = substitution_ontology.rank_results(results, freq_sort_desc, year_sort_desc).to_dict()
        return JsonResponse(
            dict(valid_query=valid_query, results=results_converted, query_translation=query_trans_string,
                 query_limit_hit="False"))
    except Exception:
        query_trans_string = "keyword query cannot be converted (syntax error)"
        traceback.print_exc(file=sys.stdout)
        return JsonResponse(
            dict(valid_query="", results=[], query_translation=query_trans_string, query_limit_hit="False"))


def get_provenance(request):
    try:
        fp2prov_ids = json.loads(str(request.GET.get("prov", "").strip()))
        result = QueryEngine.query_provenance_information(fp2prov_ids)
        return JsonResponse(dict(result=result.to_dict()))
    except:
        traceback.print_exc(file=sys.stdout)
        return HttpResponse(status=500)


def get_feedback(request):
    try:
        predication_ids = str(request.GET.get("predicationids", "").strip())
        query = str(request.GET.get("query", "").strip())
        rating = str(request.GET.get("rating", "").strip())
        userid = str(request.GET.get("userid", "").strip())

        session = SessionExtended.get()
        for pred_id in predication_ids.split(','):
            PredicationRating.insert_user_rating(session, userid, query, int(pred_id), rating)

        logging.info(f'User "{userid}" has rated "{predication_ids}" as "{rating}"')
        return HttpResponse(status=200)
    except:
        traceback.print_exc(file=sys.stdout)
        return HttpResponse(status=500)


@csrf_exempt
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
                        StatsView.stats_query_results = session.query(Predication.relation,
                                                                      Predication.extraction_type,
                                                                      func.count(Predication.relation)). \
                            group_by(Predication.relation).group_by(Predication.extraction_type).all()
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
        return super().get(request, *args, **kwargs)


class DocumentView(TemplateView):
    template_name = "ui/document.html"

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
