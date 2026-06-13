from django.db.models import Count

from .models import AuditLog


def audit_summary():
    return list(AuditLog.objects.values("method").annotate(total=Count("id")).order_by("method"))
