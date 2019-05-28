from django.shortcuts import render
from django.views.generic import TemplateView


class SearchView(TemplateView):
    template_name = "ui/search.html"

    def post(self, request, *args, **kwargs):
        context = dict()
        if "keywords" in request.POST:
            keyword_str = self.request.POST.get("keywords", "")
            if "patterns" in request.POST:
                pattern_idx = self.request.POST.get("patterns")
                context = dict(pattern_idx=pattern_idx, keyword_str=keyword_str)
            else:
                patterns = [
                    [
                        ("s1", "p1", "o1"),
                        ("s1", "p1", "o2"),
                        ("o1", "p2", "o3"),
                    ],
                    [
                        ("s1", "p1", "o1"),
                        ("o1", "p1", "o3"),
                        ("o2", "p3", "s1"),
                    ],
                ]
                context = dict(patterns=patterns, keyword_str=keyword_str)

        return render(request, self.template_name, context=context)
