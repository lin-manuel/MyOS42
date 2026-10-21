from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect

from .device_utils import get_client_ip
from .tenant_context import current_tenant_user


class RequireAuthenticatedAppMiddleware:
    """Keep application pages and APIs behind the account login boundary."""

    protected_prefixes = (
        "/dashboard/", "/home/", "/personal/", "/education/", "/finance/",
        "/bucket/", "/bucket-list/", "/projects/", "/diary/", "/reminders/",
        "/calendar/", "/notifications/", "/settings/", "/media/", "/api/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_protected = request.path.startswith(self.protected_prefixes)
        if is_protected and not request.user.is_authenticated:
            if request.path.startswith("/api/") or request.headers.get("Accept", "").startswith("application/json"):
                return JsonResponse({"ok": False, "error": "Authentication required."}, status=401)
            return redirect("accounts:login")
        token = current_tenant_user.set(request.user if request.user.is_authenticated else None)
        try:
            return self.get_response(request)
        finally:
            current_tenant_user.reset(token)

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 900


class LoginRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/accounts/login/" and request.method == "POST":
            ip = get_client_ip(request)
            key = f"login_attempts_{ip}"
            attempts = cache.get(key, 0)
            if attempts >= MAX_ATTEMPTS:
                return HttpResponseForbidden(
                    "Too many failed login attempts. Try again in 15 minutes."
                )
        response = self.get_response(request)
        if request.path == "/accounts/login/" and request.method == "POST":
            ip = get_client_ip(request)
            key = f"login_attempts_{ip}"
            if getattr(request, "_login_requires_otp", False):
                return response
            if request.user.is_authenticated:
                cache.delete(key)
                return response
            if response.status_code < 500:
                attempts = cache.get(key, 0)
                cache.set(key, attempts + 1, timeout=LOCKOUT_SECONDS)
        return response
