from django.urls import path
from django.views.decorators.cache import never_cache

from ui.views import SearchView

urlpatterns = [
    path("", never_cache(SearchView.as_view()), name="search")
]
