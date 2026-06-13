from analytics.cache import cache_metric
from apps.bucket.analytics import completion_rate, goals_per_year


def bucket_metrics(user):
    return cache_metric(
        "bucket",
        user,
        lambda: {
            "completion_rate": completion_rate(user),
            "goals_per_year": goals_per_year(user),
        },
    )
