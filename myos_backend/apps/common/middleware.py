import logging
from django.conf import settings
from django.http import HttpResponseForbidden

from .models import AuditLog

logger = logging.getLogger("myos.audit")


class LocalhostOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "LOCALHOST_ONLY", False):
            host = request.get_host().split(":")[0]
            if host not in {"127.0.0.1", "localhost"}:
                return HttpResponseForbidden("Localhost-only mode is enabled")
        return self.get_response(request)


class AuditLogMiddleware:
    TRACK_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method in self.TRACK_METHODS and not request.path.startswith("/admin/jsi18n/"):
            user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            ip = request.META.get("REMOTE_ADDR")
            AuditLog.objects.create(
                user=user,
                action="api_change",
                path=request.path,
                method=request.method,
                ip_address=ip,
                metadata={"status_code": response.status_code},
            )
            logger.info("audit action=%s method=%s path=%s user=%s", "api_change", request.method, request.path, getattr(user, "id", None))
        return response
