import importlib.util

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from config.views import APIDocsView, healthcheck, metrics_endpoint, openapi_schema


def _drf_available():
    return importlib.util.find_spec("rest_framework") is not None


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("api/health/", healthcheck, name="healthcheck"),
    path("api/metrics/", metrics_endpoint, name="metrics"),
    path("api/docs/", APIDocsView.as_view(), name="api_docs"),
    path("api/docs/openapi.json", openapi_schema, name="openapi_schema"),
]

if _drf_available():
    urlpatterns += [
        path("api/", include("apps.api.urls")),
        path("api/v1/", include("apps.api.urls")),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
