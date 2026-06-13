from django.core.cache import cache
from django.http import HttpResponseForbidden

from .device_utils import get_client_ip

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
