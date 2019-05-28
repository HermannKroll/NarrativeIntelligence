from django.http import JsonResponse
from django.views.generic import TemplateView

from mesh.data import MeSHDB
from stories.library_graph import LibraryGraph
from stories.story import StoryProcessor, MeshTagger

lg = LibraryGraph()
lg.read_from_tsv('../data/lg_pmc_sim_ami_108.tsv')

db = MeSHDB().instance()
db.load_xml('../data/desc2019.xml')


class SearchView(TemplateView):
    template_name = "ui/search.html"

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            results = dict()
            if "query" in request.GET:
                query = self.request.GET.get("query", "")
                story = StoryProcessor(lg, [MeshTagger(db)])
                results = story.query(query)
            return JsonResponse(dict(results=results))
        return super().get(request, *args, **kwargs)
