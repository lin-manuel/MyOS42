from django.apps import AppConfig


class EducationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.education"
    label = "education"

    def ready(self):
        from . import signals  # noqa: F401
