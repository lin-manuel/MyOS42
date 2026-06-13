from django.apps import AppConfig


class BucketConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bucket"
    label = "bucket"

    def ready(self):
        from . import signals  # noqa: F401
