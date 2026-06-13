from analytics.cache import cache_metric
from apps.education.analytics import education_timeline, scholarship_progress


def education_metrics(user):
    return cache_metric(
        "education",
        user,
        lambda: {
            "timeline": education_timeline(user),
            "progress": scholarship_progress(user),
        },
    )
