from analytics.cache import cache_metric
from apps.events.analytics import timeline_summary


def event_metrics(user):
    return cache_metric(
        "events",
        user,
        lambda: {
            "timeline_summary": timeline_summary(user),
        },
    )
