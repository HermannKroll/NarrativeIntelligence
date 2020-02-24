import logging
import os
import pickle
import re
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView

from narraint.graph.labeled import LabeledGraph
from narraint.mesh.data import MeSHDB
from narraint.semmeddb.dbconnection import SemMedDB
from narraint.stories.story import MeshTagger

from narraint.openie.query_engine import query_with_graph_query

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

db = MeSHDB.instance()
db.load_xml(settings.DESCRIPTOR_FILE, False, True)
mesh_tagger = MeshTagger(db)



semmed = SemMedDB(config_file=settings.SEMMEDDB_CONFIG, log_enabled=True, log_dir=settings.SEMMEDDB_LOG_DIR)
semmed.connect_to_db()
semmed.load_umls_dictionary()
semmed.load_predicates()

#if os.path.exists(settings.MESHDB_INDEX):
#    start = datetime.now()
#    with open(settings.MESHDB_INDEX, "rb") as f:
#        index = pickle.load(f)
#    db.set_index(index)
#    end = datetime.now()
#    logger.info("Index loaded in {}".format(end - start))
#else:
#
#       logger.warning("WARNING: Index file {} not found. Please create one manually.".format(settings.MESHDB_INDEX))


# END Preparation


def convert_text_to_entity(text, tagger):
    text = text.replace('_', ' ')
    if text == 'CYP3A4':
        return "1576", "Gene"

    if text.startswith('?'):
        s, s_type = text, 'VAR'
    elif text.startswith('MESH:'):
        s, s_type = text, 'MESH_MANUAL'
    else:
        s, s_type = tagger.tag_entity(text)

    return s, s_type


def convert_query_text_to_fact_patterns(query_txt, tagger, allowed_predicates):
    # split query into facts by ';'
    fact_txt = re.sub('\s+', ' ', query_txt).strip()
    facts_txt = fact_txt.strip().split(';')
    fact_patterns = []
    # explanation_str = 'Query Translation'
    explanation_str = ""
  #  explanation_str = 30 * '==' + '\n'
   # explanation_str += 30 * '==' + '\n\n'
    for fact_txt in facts_txt:
        split = fact_txt.strip().split(' ')
        # check whether the text forms a triple
        if len(split) is not 3:
            explanation_str += 'is not a triple: split:{} text:{}\n'.format(split, fact_txt)
            logger.error('is not a triple: split:{} text:{}'.format(split, fact_txt))
            return None, explanation_str

        s_t, p_t, o_t = split[0], split[1], split[2]

        s, s_type = convert_text_to_entity(s_t, tagger)
        o, o_type = convert_text_to_entity(o_t, tagger)

        if s is None:
            explanation_str += 'error unknown subject: {}\n'.format(s_t)
            logger.error('error unknown subject: {}'.format(s_t))
            return None, explanation_str

        if o is None:
            explanation_str += 'error unknown object: {}\n'.format(o_t)
            logger.error('error unknown object: {}'.format(o_t))
            return None, explanation_str

        p = p_t
      #  if p_t in allowed_predicates:
      #      p = p_t
      #  else:
      #      explanation_str += "error unknown predicate: {}\n".format(p_t)
      #      logger.error("error unknown predicate: {}".format(p_t))
      #      return None, explanation_str

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

 #   explanation_str += '\n' + 30 * '==' + '\n'
 #   explanation_str += 30 * '==' + '\n'
    return fact_patterns, explanation_str


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
                    logging.info("Selected data source is {}".format(data_source))

                    query_fact_patterns, query_trans_string = convert_query_text_to_fact_patterns(query, mesh_tagger,
                                                                                                  semmed.predicates)

                    if query_fact_patterns is None:
                        results_converted = []
                        logger.error('parsing error')
                    else:
                        if data_source == 'semmeddb':
                            pmids, titles, var_subs, var_names = semmed.query_for_fact_patterns(query_fact_patterns,
                                                                                                query)
                        else:
                            pmids, titles, var_subs, var_names = query_with_graph_query(query_fact_patterns)

                        docs = []
                        for i in range(0, len(pmids)):
                            docs.append((pmids[i], titles[i], var_subs[i], var_names))
                        results_converted.append((query_fact_patterns, docs))
                except Exception as e:
                    results_converted = []
                    query_trans_string = "keyword query cannot be converted (syntax error)"
                    logger.error(e)

            return JsonResponse(dict(results=results_converted, query_translation=query_trans_string))
        return super().get(request, *args, **kwargs)
