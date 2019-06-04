from django.http import JsonResponse
from django.views.generic import TemplateView

from mesh.data import MeSHDB
from stories.library_graph import LibraryGraph
from stories.story import StoryProcessor, MeshTagger

lg = LibraryGraph()
lg.read_from_tsv('../data/lg_pmc_sim_ami_108.tsv')

db = MeSHDB().instance()
db.load_xml('../data/desc2019.xml')

story = StoryProcessor(lg, [MeshTagger(db)])


class SearchView(TemplateView):
    template_name = "ui/search.html"

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            results = dict()
            if "query" in request.GET:
                query = self.request.GET.get("query", "").strip()
                results, query_trans = story.query(query)
                query_trans_string = str(query_trans)
                print(query_trans_string)
            return JsonResponse(dict(results=results, query_translation=query_trans_string))
        return super().get(request, *args, **kwargs)
