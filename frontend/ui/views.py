from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView

from mesh.data import MeSHDB
from stories.library_graph import LibraryGraph
from stories.story import StoryProcessor, MeshTagger

lg = LibraryGraph()
lg.read_from_tsv(settings.LIBRARY_GRAPH_FILE)

db = MeSHDB.instance()
db.load_xml(settings.DESCRIPTOR_FILE, True, True)
story = StoryProcessor(lg, [MeshTagger(db)])


class SearchView(TemplateView):
    template_name = "ui/search.html"

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            results_converted = []
            query_trans_string = ""
            if "query" in request.GET:
                query = self.request.GET.get("query", "").strip()
                results, query_trans = story.query(query)

                results_converted = []
                for res in results:
                    results_converted.append((list(res[0].facts), res[1]))

                query_trans_string = str(query_trans)
                print(query_trans_string)
            return JsonResponse(dict(results=results_converted, query_translation=query_trans_string))
        return super().get(request, *args, **kwargs)
