import asyncio
import itertools
import logging
import random
import re
import traceback
import sys

import httpx as httpx
from django.http import JsonResponse
from django.views.generic import TemplateView
from sqlalchemy import func

from narraint.backend.database import Session
from narraint.backend.models import Predication
from narraint.entity.entity import Entity
from narraint.entity.entityresolver import EntityResolver
from narraint.entity.entitytagger import EntityTagger
from narraint.entity.enttypes import GENE, SPECIES, DOSAGE_FORM, CHEMICAL, DRUG, EXCIPIENT, PLANT_FAMILY, \
    DRUGBANK_CHEMICAL, ALL, DISEASE
from narraint.extraction.predicate_vocabulary import create_predicate_vocab
from narraint.queryengine.aggregation.ontology import ResultAggregationByOntology
from narraint.queryengine.aggregation.substitution import ResultAggregationBySubstitution
from narraint.queryengine.engine import QueryEngine
from narraint.queryengine.query import GraphQuery, FactPattern
from narraint.frontend.ui.search_cache import SearchCache
from narraint.frontend.ui.autocompletion import AutocompletionUtil
from narraint.queryengine.query_hints import VAR_NAME, VAR_TYPE

variable_type_mappings = {}
for ent_typ in ALL:
    variable_type_mappings[ent_typ.lower()] = ent_typ
    variable_type_mappings[f'{ent_typ.lower()}s'] = ent_typ
# support entry of targets
variable_type_mappings["target"] = GENE
variable_type_mappings["targets"] = GENE

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)


allowed_entity_types = {CHEMICAL, DISEASE, DOSAGE_FORM, GENE, SPECIES, PLANT_FAMILY, EXCIPIENT, DRUG, DRUGBANK_CHEMICAL}

allowed_predicates = set(create_predicate_vocab().keys())
logging.info('allowed predicates are: {}'.format(allowed_predicates))


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
        return cls._instance


def check_and_convert_variable(text):
    try:
        var_name = VAR_NAME.search(text).group(1)
        m = VAR_TYPE.search(text)
        if m:
            t = m.group(1).lower()
            if t not in variable_type_mappings:
                raise ValueError('"{}" as Variable Type unknown (supported: {})'
                                 .format(t, set(variable_type_mappings.values())))
            return '{}({})'.format(var_name, variable_type_mappings[t]), variable_type_mappings[t]
        else:
            return var_name, None
    except AttributeError:
        if not VAR_NAME.search(text):
            raise ValueError('variable "{}" has no name (e.g. ?X(Chemical))'.format(text))

def convert_text_to_entity(text):
    text_low = text.replace('_', ' ').lower()
    if text.startswith('?'):
        var_string, var_type = check_and_convert_variable(text)
        e = [Entity(var_string, 'Variable')]
    elif text_low.startswith('mesh:'):
        e = [Entity(text_low.replace('mesh:', 'MESH:').replace('c', 'C').replace('d', 'D'), 'MeSH')]
    elif text_low.startswith('gene:'):
        e = [Entity(text.split(":", 1)[1], GENE)]
    elif text_low.startswith('species:'):
        e = [Entity(text.split(":", 1)[1], SPECIES)]
    elif text_low.startswith('fidx'):
        e = [Entity(text.upper(), DOSAGE_FORM)]
    else:
        try:
            e = View.instance().entity_tagger.tag_entity(text)
        except KeyError:
            raise ValueError("Unknown term: {}".format(text))
    return e


def align_triple(text: str):
    # first greedy search the predicate
    text_lower = text.lower().replace('\"', "")
    text_without_quotes = text.replace('\"', "")

    p_found = False
    pred_start, pred_len = 0, 0
    for pred in allowed_predicates:
        search = ' {} '.format(pred)
        pos = text_lower.find(search)
        if pos > 0:
            pred_start = pos
            pred_len = len(pred)
            p_found = True
            break
    if not p_found:
        raise ValueError('Cannot find a predicate in: {}'.format(text))

    subj = text_without_quotes[0:pred_start].strip()
    pred = text_without_quotes[pred_start:pred_start + pred_len + 1].strip()
    obj = text_without_quotes[pred_start + pred_len + 1:].strip()
    return subj, pred, obj


def convert_query_text_to_fact_patterns(query_txt) -> (GraphQuery, str):
    if not query_txt.strip():
        return None, "subject or object is missing"
    # remove too many spaces
    fact_txt = re.sub('\s+', ' ', query_txt).strip()
    # split query into facts by '.'
    facts_txt = fact_txt.strip().replace(';', '.').split('.')
    graph_query = GraphQuery()
    explanation_str = ""
    for fact_txt in facts_txt:
        # skip empty facts
        if not fact_txt.strip():
            continue
        s_t, p_t, o_t = None, None, None
        try:
            # check whether the text forms a triple
            s_t, p_t, o_t = align_triple(fact_txt)
        except ValueError:
            explanation_str += 'Cannot find a predicate in: {}'.format(fact_txt)
            logger.error('Cannot find a predicate in: {}'.format(fact_txt))
            return None, explanation_str

        try:
            s = convert_text_to_entity(s_t)
        except ValueError as e:
            explanation_str += '{} (subject error)\n'.format(e)
            logger.error('error unknown subject: {}'.format(e))
            return None, explanation_str

        try:
            o = convert_text_to_entity(o_t)
        except ValueError as e:
            explanation_str += '{} (object error)\n'.format(e)
            logger.error('error unknown object: {}'.format(e))
            return None, explanation_str

        p = p_t.lower()
        if p not in allowed_predicates:
            explanation_str += "{} (predicate error)\n".format(p_t)
            logger.error("error unknown predicate: {}".format(p_t))
            return None, explanation_str

        explanation_str += '{}\t----->\t({}, {}, {})\n'.format(fact_txt.strip(), s, p, o)
        graph_query.add_fact_pattern(FactPattern(s, p, o))

    return graph_query, explanation_str


def convert_graph_patterns_to_nt(query_txt):
    fact_txt = re.sub('\s+', ' ', query_txt).strip()
    facts_split = fact_txt.strip().replace(';', '.').split('.')
    nt_string = ""
    var_dict = {}
    for f in facts_split:
        # skip empty facts
        if not f.strip():
            continue
        s, p, o = align_triple(f.strip())

        if s.startswith('?'):
            var_name = VAR_NAME.search(s).group(1)
            var_type = VAR_TYPE.search(s)
            if var_name not in var_dict:
                var_dict[var_name], _ = check_and_convert_variable(s)
            if var_type:
                var_dict[var_name], _ = check_and_convert_variable(s)
        if o.startswith('?'):
            var_name = VAR_NAME.search(o).group(1)
            var_type = VAR_TYPE.search(o)
            if var_name not in var_dict:
                var_dict[var_name], _ = check_and_convert_variable(o)
            if var_type:
                var_dict[var_name], _ = check_and_convert_variable(o)

    for f in facts_split:
        # skip empty facts
        if not f.strip():
            continue
        s, p, o = align_triple(f.strip())

        if s.startswith('?'):
            s = var_dict[VAR_NAME.search(s).group(1)]
        if o.startswith('?'):
            o = var_dict[VAR_NAME.search(o).group(1)]

        nt_string += "<{}>\t<{}>\t<{}>\t.\n".format(s, p, o)
    return nt_string[0:-1]  # remove last \n


def count_variables_in_query(graph_query: GraphQuery):
    var_set = set()
    for fp in graph_query.fact_patterns:
        s = next(iter(fp.subjects)).entity_id
        s_t = next(iter(fp.subjects)).entity_type
        o = next(iter(fp.objects)).entity_id
        o_t = next(iter(fp.objects)).entity_type
        if s_t == 'Variable':
            var_set.add(VAR_NAME.search(s).group(1))
        if o_t == 'Variable':
            var_set.add(VAR_NAME.search(o).group(1))
    return len(var_set)


async def get_flavor(request):
    print("Getting flavor...")
    await asyncio.sleep(2)
    print("Returning flavor")
    return JsonResponse(dict(data=random.choice(
        [
            "Sweet Baby Ray's",
            "Stubb's Original",
            "Famous Dave's",
        ]
    )))


async def get_autocompletion(request):
    completion_terms = []
    if "term" in request.GET:
        search_string = str(request.GET.get("term", "").strip())
        completion_terms = View.instance().autocompletion.compute_autocompletion_list(search_string)
        logging.info(f'For {search_string} sending completion terms: {completion_terms}')
    return JsonResponse(dict(terms=completion_terms))


async def get_check_query(request):
    if "query" in request.GET:
        search_string = str(request.GET.get("query", "").strip())
        logging.info(f'checking query: {search_string}')
        query_fact_patterns, query_trans_string = convert_query_text_to_fact_patterns(search_string)
        if query_fact_patterns:
            logging.info('query is valid')
            return JsonResponse(dict(valid="True"))
        else:
            logging.info(f'query is not valid: {query_trans_string}')
            return JsonResponse(dict(valid=query_trans_string))
    return JsonResponse(dict(valid="False"))

async def get_query(request):
    results_converted = []
    if "query" in request.GET:
        valid_query = False
        query_limit_hit = False
        try:
            query = str(request.GET.get("query", "").strip())
            data_source = str(request.GET.get("data_source", "").strip())
            outer_ranking = str(request.GET.get("outer_ranking", "").strip())
            # inner_ranking = str(request.GET.get("inner_ranking", "").strip())
            logging.info(f'Query string is: {query}')
            logging.info("Selected data source is {}".format(data_source))
            logging.info('Strategy for outer ranking: {}'.format(outer_ranking))
            # logging.info('Strategy for inner ranking: {}'.format(inner_ranking))

            query_fact_patterns, query_trans_string = convert_query_text_to_fact_patterns(query)
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
            elif outer_ranking == 'outer_ranking_ontology' and count_variables_in_query(
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
        except Exception:
            results_converted = []
            query_trans_string = "keyword query cannot be converted (syntax error)"
            traceback.print_exc(file=sys.stdout)

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
                    session = Session.get()
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
