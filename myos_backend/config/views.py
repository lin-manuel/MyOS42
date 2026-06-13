import importlib.util
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from apps.common.metrics import REGISTRY


def _drf_available():
    return importlib.util.find_spec("rest_framework") is not None


def healthcheck(request):
    started = time.perf_counter()
    db_ok = True
    cache_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        db_ok = False

    try:
        cache.set("healthcheck", "ok", timeout=5)
        cache_ok = cache.get("healthcheck") == "ok"
    except Exception:
        cache_ok = False

    status_code = 200 if db_ok and cache_ok else 503
    return JsonResponse(
        {
            "status": "ok" if status_code == 200 else "degraded",
            "database": db_ok,
            "cache": cache_ok,
            "drf_available": _drf_available(),
            "environment": "development" if settings.DEBUG else "production",
            "response_ms": round((time.perf_counter() - started) * 1000, 2),
        },
        status=status_code,
    )


def metrics_endpoint(request):
    payload = REGISTRY.render_prometheus()
    return HttpResponse(payload, content_type="text/plain; version=0.0.4")


class APIDocsView(TemplateView):
    template_name = "api_docs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["api_version"] = "v1"
        context["drf_available"] = _drf_available()
        return context


def openapi_schema(request):
    routes = {
        "auth": [
            "/api/v1/auth/signup/",
            "/api/v1/auth/verify-otp/",
            "/api/v1/auth/token/",
            "/api/v1/auth/password-reset/request/",
        ],
        "dashboard": ["/api/v1/dashboard/"],
        "projects": [
            "/api/v1/projects/",
            "/api/v1/project-tasks/",
            "/api/v1/project-notes/",
            "/api/v1/project-attachments/",
        ],
        "finance": ["/api/v1/finance/transactions/", "/api/v1/finance/budgets/", "/api/v1/finance/savings-goals/"],
        "education": ["/api/v1/education/records/", "/api/v1/education/scholarships/", "/api/v1/education/documents/"],
        "diary": ["/api/v1/diary/"],
        "media": ["/api/v1/media/", "/api/v1/media-progress/", "/api/v1/media-seasons/", "/api/v1/media-episodes/"],
        "bucket": ["/api/v1/bucket/categories/", "/api/v1/bucket/items/"],
        "notifications": ["/api/v1/notifications/"],
        "events": ["/api/v1/events/"],
        "search": ["/api/v1/search/"],
    }
    return JsonResponse(
        {
            "openapi": "3.0.3",
            "info": {"title": "MyOS API", "version": "1.0.0"},
            "servers": [{"url": "/api/v1"}],
            "paths": {route: {"get": {"summary": route}} for routeset in routes.values() for route in routeset},
            "x-myos-routes": routes,
        }
    )
