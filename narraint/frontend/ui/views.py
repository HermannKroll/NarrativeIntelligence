import itertools
import logging
import re
import traceback
import sys

from django.http import JsonResponse
from django.views.generic import TemplateView
from sqlalchemy import func

from narraint.backend.database import Session
from narraint.backend.models import Predication
from narraint.entity.entity import Entity
from narraint.entity.entitytagger import EntityTagger
from narraint.entity.enttypes import GENE, SPECIES, DOSAGE_FORM, CHEMICAL, DRUG, EXCIPIENT, PLANT_FAMILY, \
    DRUGBANK_CHEMICAL, ALL
from narraint.extraction.versions import PATHIE_EXTRACTION, OPENIE_EXTRACTION
from narraint.extraction.predicate_vocabulary import create_predicate_vocab
from narraint.queryengine.aggregation.ontology import ResultAggregationByOntology
from narraint.queryengine.aggregation.substitution import ResultAggregationBySubstitution
from narraint.queryengine.engine import QueryEngine
from narraint.queryengine.query import GraphQuery, FactPattern
from narraint.queryengine.result import QueryDocumentResult
from narraint.frontend.ui.search_cache import SearchCache

VAR_NAME = re.compile(r'(\?\w+)')
VAR_TYPE = re.compile(r'\((\w+)\)')

variable_type_mappings = {}
for ent_typ in ALL:
    variable_type_mappings[ent_typ.lower()] = ent_typ
    variable_type_mappings[f'{ent_typ.lower()}s'] = ent_typ

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

allowed_predicates = set(create_predicate_vocab().keys())
logging.info('allowed predicates are: {}'.format(allowed_predicates))

query_engine = QueryEngine()
entity_tagger = EntityTagger()
cache = SearchCache()

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
        if var_type == CHEMICAL:
            e = [Entity(var_string, 'Variable'),
                 Entity(var_string.replace(f'({CHEMICAL})', f'({DRUG})'), 'Variable'),
                 Entity(var_string.replace(f'({CHEMICAL})', f'({EXCIPIENT})'), 'Variable'),
                 Entity(var_string.replace(f'({CHEMICAL})', f'({DRUGBANK_CHEMICAL})'), 'Variable')]
        else:
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
            e = entity_tagger.tag_entity(text)
        except KeyError:
            raise ValueError("Don't know how to understand: {}".format(text))
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
            explanation_str += 'error unknown subject: {}\n'.format(e)
            logger.error('error unknown subject: {}'.format(e))
            return None, explanation_str

        try:
            o = convert_text_to_entity(o_t)
        except ValueError as e:
            explanation_str += 'error unknown object: {}\n'.format(e)
            logger.error('error unknown object: {}'.format(e))
            return None, explanation_str

        p = p_t.lower()
        if p not in allowed_predicates:
            explanation_str += "error unknown predicate: {}\n".format(p_t)
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
        s = fp.subjects[0].entity_id
        s_t = fp.subjects[0].entity_type
        o = fp.objects[0].entity_id
        o_t = fp.objects[0].entity_type
        if s_t == 'Variable':
            var_set.add(VAR_NAME.search(s).group(1))
        if o_t == 'Variable':
            var_set.add(VAR_NAME.search(o).group(1))
    return len(var_set)


class SearchView(TemplateView):
    template_name = "ui/search.html"

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            results_converted = []
            query_trans_string = ""
            nt_string = ""
            if "query" in request.GET:
                try:
                    query = str(self.request.GET.get("query", "").strip())
                    data_source = str(self.request.GET.get("data_source", "").strip())
                    outer_ranking = str(self.request.GET.get("outer_ranking", "").strip())
                    inner_ranking = str(self.request.GET.get("inner_ranking", "").strip())
                    logging.info("Selected data source is {}".format(data_source))
                    logging.info('Strategy for outer ranking: {}'.format(outer_ranking))
                    logging.info('Strategy for inner ranking: {}'.format(inner_ranking))

                    query_fact_patterns, query_trans_string = convert_query_text_to_fact_patterns(query)
                    if data_source not in ["PMC", "PubMed", "PMC_Path", "PubMed_Path"]:
                        results_converted = []
                        query_trans_string = "Data source is unknown"
                        nt_string = ""
                        logger.error('parsing error')
                    elif outer_ranking not in ["outer_ranking_substitution", "outer_ranking_ontology"]:
                        query_trans_string = "Outer ranking strategy is unknown"
                        nt_string = ""
                        logger.error('parsing error')
                    elif query_fact_patterns is None:
                        results_converted = []
                        nt_string = ""
                        logger.error('parsing error')
                    elif outer_ranking == 'outer_ranking_ontology' and count_variables_in_query(
                            query_fact_patterns) > 1:
                        results_converted = []
                        nt_string = ""
                        query_trans_string = "Do not support multiple variables in an ontology-based ranking"
                        logger.error("Do not support multiple variables in an ontology-based ranking")
                    else:
                        nt_string = convert_graph_patterns_to_nt(query)
                        if 'Path' in data_source:
                            document_collection = data_source.replace('_Path', '')
                            extraction_type = PATHIE_EXTRACTION
                        else:
                            document_collection = data_source
                            extraction_type = OPENIE_EXTRACTION
                        try:
                            cached_results = cache.load_result_from_cache(document_collection, query_fact_patterns)
                        except Exception:
                            logging.error('Cannot load query result from cache...')
                            cached_results = None
                        if cached_results:
                            logging.info('Cache hit - {} results loaded'.format(len(cached_results)))
                            results = cached_results
                        else:
                            results = query_engine.process_query_with_expansion(query_fact_patterns, document_collection,
                                                                                extraction_type="", query=query)
                            logging.info('Write results to cache...')
                            try:
                                cache.add_result_to_cache(document_collection, query_fact_patterns, results)
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
                    nt_string = ""
                    traceback.print_exc(file=sys.stdout)

            return JsonResponse(
                dict(results=results_converted, query_translation=query_trans_string, nt_string=nt_string))
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
