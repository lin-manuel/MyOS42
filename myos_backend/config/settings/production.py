from .base import *  # noqa: F401,F403
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet


DEBUG = False
if not SECRET_KEY or SECRET_KEY.startswith(("change-me", "replace-")):
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY before using production settings.")
if not FERNET_KEY:
    raise ImproperlyConfigured("Set FERNET_KEY before using production settings.")
try:
    Fernet(FERNET_KEY.encode("ascii"))
except (ValueError, TypeError, UnicodeEncodeError) as exc:
    raise ImproperlyConfigured("FERNET_KEY must be a valid Fernet key.") from exc
LOCALHOST_ONLY = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
