import os
import pickle
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView

from mesh.data import MeSHDB
from stories.library_graph import LibraryGraph
from stories.story import StoryProcessor, MeshTagger

from semmeddb.dbconnection import SemMedDB

# BEGIN Preparation
#lg = LibraryGraph()
#lg.read_from_tsv(settings.LIBRARY_GRAPH_FILE)

#story = StoryProcessor(lg, [MeshTagger(db)])

db = MeSHDB.instance()
db.load_xml(settings.DESCRIPTOR_FILE, False, True)
mesh_tagger = MeshTagger(db)

semmed = SemMedDB(settings.SEMMEDDB_CONFIG)
semmed.connect_to_db()
semmed.load_umls_dictionary()
semmed.load_predicates()

if os.path.exists(settings.MESHDB_INDEX):
    start = datetime.now()
    with open(settings.MESHDB_INDEX, "rb") as f:
        index = pickle.load(f)
    db.set_index(index)
    end = datetime.now()
    print("Index loaded in {}".format(end - start))
else:
    print("WARNING: Index file {} not found. Please create one manually.".format(settings.MESHDB_INDEX))


# END Preparation


def convert_text_to_entity(text, tagger):
    if text.startswith('?'):
        s, s_type = text, 'VAR'
    elif text.startswith('MESH:'):
        s, s_type = text, 'MESH_MANUAL'
    else:
        s, s_type = tagger.tag_entity(text)

    return s, s_type


def convert_query_text_to_fact_patterns(query_txt, tagger, allowed_predicates):
    # split query into facts by ';'
    facts_txt = query_txt.strip().split(';')
    fact_patterns = []
    #explanation_str = 'Query Translation'
    explanation_str = 60*'==' + '\n'
    explanation_str += 60 * '==' + '\n'
    for fact_txt in facts_txt:
        s_t, p_t, o_t = fact_txt.strip().split(' ')

        s, s_type = convert_text_to_entity(s_t, tagger)
        o, o_type = convert_text_to_entity(o_t, tagger)

        if s is None:
            print('error unknown subject: {}'.format(s_t))
            return None

        if o is None:
            print('error unknown object: {}'.format(o_t))
            return None

        if p_t in allowed_predicates:
            p = p_t
        else:
            print("error unknown predicate: {}".format(p_t))
            return None

        explanation_str += '\n {}\t----->\t({}, {}, {})'.format(fact_txt, s, p, o)
        fact_patterns.append((s, p, o))

    explanation_str += '\n' + 60 * '==' + '\n'
    explanation_str += 60 * '==' + '\n'
    return fact_patterns, explanation_str


class SearchView(TemplateView):
    template_name = "ui/search.html"

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            results_converted = []
            query_trans_string = ""
            if "query" in request.GET:
                query = self.request.GET.get("query", "").strip()

                query_fact_patterns, query_trans_string = convert_query_text_to_fact_patterns(query, mesh_tagger, semmed.predicates)
                pmids, var_subs, var_names = semmed.query_for_fact_patterns(query_fact_patterns)
                docs = []
                for i in range(0, len(pmids)-1):
                    docs.append((pmids[i], var_subs[i], var_names))

                results_converted.append((query_fact_patterns, docs))

                #results, query_trans = story.query(query)

                #results_converted = []
                #for res in results:
                #    results_converted.append((list(res[0].facts), res[1]))

                #query_trans_string = str(query_trans)
                #print(query_trans_string)
            return JsonResponse(dict(results=results_converted, query_translation=query_trans_string))
        return super().get(request, *args, **kwargs)
