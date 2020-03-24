import logging
import os
import pickle
import re
import traceback
import sys
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView
from narraint.mesh.data import MeSHDB
from narraint.stories.story import MeshTagger
from narraint.queryengine.engine import QueryEngine

VAR_NAME = re.compile(r'(\?\w+)')
VAR_TYPE = re.compile(r'\((\w+)\)')

allowed_variable_types = ["Chemical", "Disease", "DosageForm", "Gene", "Species"]

allowed_predicates = ['administered to', 'affects', 'associated with', 'augments', 'causes', 'coexists with',
                      'complicates', 'converts to', 'diagnoses', 'disrupts', 'inhibits', 'interacts with', 'isa',
                      'location of', 'manifestation of', 'method of', 'occurs in', 'part of', 'precedes', 'predisposes',
                      'prevents', 'process of', 'produces', 'stimulates', 'treats', 'uses', 'compared with',
                      'different from', 'higher than', 'lower than', 'same as']

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)
query_engine = QueryEngine()
db = MeSHDB.instance()
db.load_xml(settings.DESCRIPTOR_FILE, False, True)
mesh_tagger = MeshTagger(db)

try:
    if os.path.exists(settings.MESHDB_INDEX):
        start = datetime.now()
        print(settings.MESHDB_INDEX)
        with open(settings.MESHDB_INDEX, "rb") as f:
            index = pickle.load(f)
        db.set_index(index)
        end = datetime.now()
        logger.info("Index loaded in {}".format(end - start))
    else:
        logger.warning("WARNING: Index file {} not found. Please create one manually.".format(settings.MESHDB_INDEX))
except Exception:
    traceback.print_exc(file=sys.stdout)


# END Preparation
def check_and_convert_variable(text):
    var_name = VAR_NAME.search(text).group(1)
    m = VAR_TYPE.search(text)
    if m:
        t = m.group(1).capitalize()
        if t not in allowed_variable_types:
            raise ValueError('"{}" as Variable Type unknown (supported: {})'.format(t, allowed_variable_types))
        return '{}({})'.format(var_name, t)


def convert_text_to_entity(text, tagger):
    text_low = text.replace('_', ' ').lower()
    if text.startswith('?'):
        s, s_type = check_and_convert_variable(text), 'Variable'
    elif text.startswith('mesh:'):
        s, s_type = text_low.replace('mesh:', 'MESH:').replace('c', 'C').replace('d', 'D'), 'MeSH'
    elif text.startswith('gene:'):
        s, s_type = text.split(":", 1)[1], "Gene"
    elif text.startswith('species:'):
        s, s_type = text.split(":", 1)[1], "Species"
    else:
        s, s_type = tagger.tag_entity(text)
    if not s:
        raise ValueError("Don't know how to understand: {}".format(text))
    return s, s_type


def convert_query_text_to_fact_patterns(query_txt, tagger):
    # split query into facts by ';'
    fact_txt = re.sub('\s+', ' ', query_txt).strip()
    facts_txt = fact_txt.strip().replace(';', '.').split('.')
    fact_patterns = []
    explanation_str = ""
    for fact_txt in facts_txt:
        split = fact_txt.strip().split(' ')
        # check whether the text forms a triple
        if len(split) is not 3:
            explanation_str += 'is not a triple: split:{} text:{}\n'.format(split, fact_txt)
            logger.error('is not a triple: split:{} text:{}'.format(split, fact_txt))
            return None, explanation_str

        s_t, p_t, o_t = split[0], split[1], split[2]
        try:
            s, s_type = convert_text_to_entity(s_t, tagger)
        except ValueError as e:
            explanation_str += 'error unknown subject: {}\n'.format(e)
            logger.error('error unknown subject: {}'.format(e))
            return None, explanation_str

        try:
            o, o_type = convert_text_to_entity(o_t, tagger)
        except ValueError as e:
            explanation_str += 'error unknown object: {}\n'.format(e)
            logger.error('error unknown object: {}'.format(e))
            return None, explanation_str

        p = p_t.lower().replace('_', ' ')
        if p not in allowed_predicates:
            explanation_str += "error unknown predicate: {}\n".format(p_t)
            logger.error("error unknown predicate: {}".format(p_t))
            return None, explanation_str

        explanation_str += '{}\t----->\t({}, {}, {})\n'.format(fact_txt, s, p, o)
        fact_patterns.append((s, p, o))

    # check for at least 1 entity
    entity_check = False
    for s, p, o in fact_patterns:
        if not s.startswith('?') or not o.startswith('?'):
            entity_check = True
            break
    if not entity_check:
        explanation_str += "no entity included in query - error\n"
        return None, explanation_str

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
        split = f.strip().split(' ')
        s, p, o = split[0], split[1], split[2]

        if s.startswith('?'):
            var_name = VAR_NAME.search(s).group(1)
            var_type = VAR_TYPE.search(s)
            if var_name not in var_dict:
                var_dict[var_name] = '{}'.format(var_name)
            if var_type:
                var_dict[var_name] = '{}({})'.format(var_name, var_type.group(1))
        if o.startswith('?'):
            var_name = VAR_NAME.search(o).group(1)
            var_type = VAR_TYPE.search(o)
            if var_name not in var_dict:
                var_dict[var_name] = '{}'.format(var_name)
            if var_type:
                var_dict[var_name] = '{}({})'.format(var_name, var_type.group(1))

    for f in facts_split:
        split = f.strip().split(' ')
        s, p, o = split[0], split[1], split[2]

        if s.startswith('?'):
            s = var_dict[VAR_NAME.search(s).group(1)]
        if o.startswith('?'):
            o = var_dict[VAR_NAME.search(o).group(1)]

        nt_string += "<{}>\t<{}>\t<{}>\t.\n".format(s, p, o)
    return nt_string[0:-1]  # remove last \n


class SearchView(TemplateView):
    template_name = "ui/search.html"

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            results_converted = []
            query_trans_string = ""
            if "query" in request.GET:
                try:
                    query = self.request.GET.get("query", "").strip()
                    data_source = self.request.GET.get("data_source", "").strip()
                    # logging.info("Selected data source is {}".format(data_source))

                    query_fact_patterns, query_trans_string = convert_query_text_to_fact_patterns(query, mesh_tagger)
                    if query_fact_patterns is None:
                        results_converted = []
                        nt_string = ""
                        logger.error('parsing error')
                    else:
                        nt_string = convert_graph_patterns_to_nt(query)
                        #  if data_source == 'semmeddb':
                        #      results_converted = []
                        #       query_trans_string = "currently not supported"
                        #  pmids, titles, var_subs, var_names = semmed.query_for_fact_patterns(query_fact_patterns,
                        #                                                                     query)
                        #    else:
                        results_converted = []
                        aggregated_result = query_engine.query_with_graph_query(query_fact_patterns, query)
                        for var_names, var_subs, d_ids, titles, explanations in aggregated_result.get_and_rank_results()[
                                                                                0:25]:
                            results_converted.append(list((var_names, var_subs, d_ids, titles, explanations)))


                except Exception:
                    results_converted = []
                    query_trans_string = "keyword query cannot be converted (syntax error)"
                    traceback.print_exc(file=sys.stdout)

            return JsonResponse(
                dict(results=results_converted, query_translation=query_trans_string, nt_string=nt_string))
        return super().get(request, *args, **kwargs)
