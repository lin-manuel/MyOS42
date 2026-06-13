import os

try:
    from celery import Celery
except ImportError:  # pragma: no cover - optional dependency in this environment
    Celery = None


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")


if Celery is not None:
    app = Celery("myos_backend")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()
else:  # pragma: no cover - fallback placeholder
    app = None
