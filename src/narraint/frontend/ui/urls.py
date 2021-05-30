from django.urls import path
from django.views.decorators.cache import never_cache

from narraint.frontend.ui.views import SearchView, get_autocompletion, get_check_query, get_query, get_feedback, post_report

urlpatterns = [
    path("", never_cache(SearchView.as_view()), name="search"),
    path("query", get_query, name="query"),
    path("autocompletion", get_autocompletion, name="autocompletion"),
    path("check", get_check_query, name="check"),
    path("feedback", get_feedback, name="feedback"),
    path("report", post_report, name="report")
]
