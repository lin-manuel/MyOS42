from django.db.models import Count

from .models import Event


def timeline_summary(user):
    return list(
        Event.objects.filter(user=user)
        .values("event_type")
        .annotate(total=Count("id"))
        .order_by("event_type")
    )
