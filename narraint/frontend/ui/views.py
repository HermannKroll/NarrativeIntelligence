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
from narraint.entity.entitytagger import EntityTagger
from narraint.entity.enttypes import GENE, SPECIES, DOSAGE_FORM
from narraint.extraction.versions import PATHIE_EXTRACTION, OPENIE_EXTRACTION
from narraint.extraction.predicate_vocabulary import create_predicate_vocab
from narraint.queryengine.aggregation.ontology import ResultAggregationByOntology
from narraint.queryengine.aggregation.substitution import ResultAggregationBySubstitution
from narraint.queryengine.engine import QueryEngine
from narraint.queryengine.result import QueryDocumentResult

VAR_NAME = re.compile(r'(\?\w+)')
VAR_TYPE = re.compile(r'\((\w+)\)')

variable_type_mappings = {"chemical": "Chemical",
                          "chemicals": "Chemical",
                          "disease": "Disease",
                          "diseases": "Disease",
                          "dosageform": "DosageForm",
                          "dosageforms": "DosageForm",
                          "gene": "Gene",
                          "genes": "Gene",
                          "species": "Species"}

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

allowed_predicates = list(create_predicate_vocab().keys())
allowed_predicates.append("dosageform")
logging.info('allowed predicates are: {}'.format(allowed_predicates))

query_engine = QueryEngine()
entity_tagger = EntityTagger()


def check_and_convert_variable(text):
    var_name = VAR_NAME.search(text).group(1)
    m = VAR_TYPE.search(text)
    if m:
        t = m.group(1).lower()
        if t not in variable_type_mappings:
            raise ValueError('"{}" as Variable Type unknown (supported: {})'
                             .format(t, list(variable_type_mappings.values())))
        return '{}({})'.format(var_name, variable_type_mappings[t])
    else:
        return var_name


def convert_text_to_entity(text):
    text_low = text.replace('_', ' ').lower()
    if text.startswith('?'):
        s, s_type = check_and_convert_variable(text), 'Variable'
    elif text_low.startswith('mesh:'):
        s, s_type = text_low.replace('mesh:', 'MESH:').replace('c', 'C').replace('d', 'D'), 'MeSH'
    elif text_low.startswith('gene:'):
        s, s_type = text.split(":", 1)[1], GENE
    elif text_low.startswith('species:'):
        s, s_type = text.split(":", 1)[1], SPECIES
    elif text_low.startswith('fidx'):
        s, s_type = text.upper(), DOSAGE_FORM
    else:
        try:
            s, s_type = entity_tagger.tag_entity(text)
        except KeyError:
            raise ValueError("Don't know how to understand: {}".format(text))
    return s, s_type


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


def convert_query_text_to_fact_patterns(query_txt):
    # remove too many spaces
    fact_txt = re.sub('\s+', ' ', query_txt).strip()
    # split query into facts by '.'
    facts_txt = fact_txt.strip().replace(';', '.').split('.')
    fact_patterns = []
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
            s, s_type = convert_text_to_entity(s_t)
        except ValueError as e:
            explanation_str += 'error unknown subject: {}\n'.format(e)
            logger.error('error unknown subject: {}'.format(e))
            return None, explanation_str

        try:
            o, o_type = convert_text_to_entity(o_t)
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
        fact_patterns.append((s, s_type, p, o, o_type))

    # check for at least 1 entity
    #   entity_check = False
    #  for s, p, o in fact_patterns:
    #     if not s.startswith('?') or not o.startswith('?'):
    #        entity_check = True
    #       break
    # if not entity_check:
    #    explanation_str += "no entity included in query - error\n"
    #   return None, explanation_str

    # check if the query is one connected graph
    #  g = LabeledGraph()
    #  for s, p, o in fact_patterns:
    #      g.add_edge(p, s, o)
    # there are multiple connected components - stop
    #  con_comp = g.compute_connectivity_components()
    #  if len(con_comp) != 1:
    #      explanation_str += "query consists of multiple graphs (query must be one connectivity component)\n"
    #     return None, explanation_str

    return fact_patterns, explanation_str


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
                var_dict[var_name] = check_and_convert_variable(s)
            if var_type:
                var_dict[var_name] = check_and_convert_variable(s)
        if o.startswith('?'):
            var_name = VAR_NAME.search(o).group(1)
            var_type = VAR_TYPE.search(o)
            if var_name not in var_dict:
                var_dict[var_name] = check_and_convert_variable(o)
            if var_type:
                var_dict[var_name] = check_and_convert_variable(o)

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


def count_variables_in_query(patterns):
    var_set = set()
    for s, s_t, p, o, o_t in patterns:
        if s_t == 'Variable':
            var_set.add(VAR_NAME.search(s).group(1))
        if o_t == 'Variable':
            var_set.add(VAR_NAME.search(o).group(1))
    return len(var_set)


def _compute_entity_list(entity, entity_type):
    """
    Transforms an entity and entity type into a list
    If the entity is a list of tree numbers nothing happens
    else the entity will be packed into a list
    :param entity: an entity id
    :param entity_type: the entity type
    :return: returns the entity id packed in a list
    """
    if entity_type == 'MESH_ONTOLOGY':
        # it is already a list of tree numbers
        return entity
    else:
        return [entity]


def _merge_results(results: [QueryDocumentResult]) -> [QueryDocumentResult]:
    """
    Merges a list of document results and eliminates duplicated documents
    :param results: a list of QueryDocumentResult
    :return: a list of unique QueryDocumentResult
    """
    result_index = {}
    unique_results = []
    for r in results:
        if r.document_id in result_index:
            is_new_document = True
            for existing in result_index[r.document_id]:
                if existing == r:
                    is_new_document = False
                    break
            if is_new_document:
                result_index[r.document_id].append(r)
                unique_results.append(r)
        else:
            result_index[r.document_id] = [r]
            unique_results.append(r)
    return unique_results


def process_query(query_fact_patterns, data_source, query):
    """
    Executes the query fact patterns as a SQL query and collects all results
    Expands the query automatically, if e.g. a MeSH descriptor has several tree numbers
    :param query_fact_patterns: a list of query fact patterns
    :param data_source: the data source PubMed / PMC
    :param query: the query as the input string for logging
    :return: a list of QueryDocumentResults
    """
    query_fact_patterns_expanded = []
    expand_query = False
    for idx, qp in enumerate(query_fact_patterns):
        exp_cond1 = qp[1] == 'MESH_ONTOLOGY' and len(qp[0]) > 1
        exp_cond2 = qp[4] == 'MESH_ONTOLOGY' and len(qp[3]) > 1

        if exp_cond1 or exp_cond2:
            expand_query = True
            subj_entities = _compute_entity_list(qp[0], qp[1])
            subj_type = qp[1]
            predicates = [qp[2]]
            obj_entities = _compute_entity_list(qp[3], qp[4])
            obj_type = qp[4]
            cross_product = list(itertools.product(subj_entities, [subj_type], predicates, obj_entities, [obj_type]))
            query_fact_patterns_expanded.append(cross_product)
        else:
            query_fact_patterns_expanded.append(qp)

    if 'Path' in data_source:
        data_source = data_source.replace('_Path', '')
        extraction_type = PATHIE_EXTRACTION
    else:
        extraction_type = OPENIE_EXTRACTION

    if expand_query:
        query_fact_patterns_expanded = list(itertools.product(*query_fact_patterns_expanded))
        logging.info('The query will be expanded into {} queries'.format(len(query_fact_patterns_expanded)))
        part_result = []
        for query_fact_patterns in query_fact_patterns_expanded:
            part_result.extend(query_engine.query_with_graph_query(list(query_fact_patterns), data_source,
                                                                   extraction_type, query))
        results = _merge_results(part_result)

    else:
        results = query_engine.query_with_graph_query(query_fact_patterns_expanded, data_source,
                                                      extraction_type, query)
    return results


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
                        results = process_query(query_fact_patterns, data_source, query)
                        results_converted = []
                        if outer_ranking == 'outer_ranking_substitution':
                            substitution_aggregation = ResultAggregationBySubstitution()
                            results_converted = substitution_aggregation.rank_results(results).to_dict()
                        elif outer_ranking == 'outer_ranking_ontology':
                            substitution_ontology = ResultAggregationByOntology()
                            results_converted = substitution_ontology.rank_results(results).to_dict()
                    # with open('last_query.json', 'wt') as f:
                    #     pprint(results_converted, f)
                #      for var_names, var_subs, d_ids, titles, explanations in aggregated_result.get_and_rank_results()[
                #                                                             0:30]:
                #        results_converted.append(list((var_names, var_subs, d_ids, titles, explanations)))
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
