"""frontend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.decorators.cache import never_cache

from narraint.frontend.frontend.settings.base import INSTALLED_APPS, ADMIN_ENABLED
from narraint.frontend.ui.views import StatsView, HelpView, DocumentView, DrugOverviewView, DrugOverviewIndexView, \
    SearchView, SwaggerUIView

urlpatterns = [
    path(r'', include('ui.urls')),
    path("stats/", never_cache(StatsView.as_view()), name="stats"),
    path("help/", never_cache(HelpView.as_view()), name="help"),
    path("document/", never_cache(DocumentView.as_view()), name="document"),
    path('drug_overview/', DrugOverviewView.as_view(), name='drug_overview'),
    path('drug_overview_index/', DrugOverviewIndexView.as_view(), name='drug_overview_index'),
    path("", never_cache(SearchView.as_view()), name="search"),
    path('swagger-ui/', SwaggerUIView.as_view(
        extra_context={'schema_url': 'openapi-schema'}
    ), name='swagger-ui')
]

if ADMIN_ENABLED is True:
    urlpatterns.append(path('admin/', admin.site.urls))
    INSTALLED_APPS.append('django.contrib.admin')
