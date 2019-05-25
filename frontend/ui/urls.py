from django.urls import path

from ui.views import SearchView

urlpatterns = [
    path("", SearchView.as_view(), name="search")
]
