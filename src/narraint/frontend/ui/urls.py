from django.urls import path
from django.views.decorators.cache import never_cache

from narraint.frontend.ui.views import SearchView, get_autocompletion, get_check_query, get_query, get_feedback, \
    post_report, get_provenance, get_document_graph, get_tree_info, get_query_sub_count

urlpatterns = [
    path("", never_cache(SearchView.as_view()), name="search"),
    path("query", get_query, name="query"),
    path("query_sub_count", get_query_sub_count, name="query_sub_count"),
    path("autocompletion", get_autocompletion, name="autocompletion"),
    path("check", get_check_query, name="check"),
    path("feedback", get_feedback, name="feedback"),
    path("provenance", get_provenance, name="provenance"),
    path("report", post_report, name="report"),
    path("document_graph", get_document_graph, name="document_graph"),
    path("tree_info", get_tree_info, name="tree_info")
]
