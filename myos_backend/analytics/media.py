from analytics.cache import cache_metric
from apps.media.analytics import completion_rate, genre_distribution, movies_per_month, watch_history, watch_time


def media_metrics(user):
    return cache_metric(
        "media",
        user,
        lambda: {
            "watch_time": watch_time(user),
            "completion_rate": completion_rate(user),
            "genre_distribution": genre_distribution(user),
            "movies_per_month": movies_per_month(user),
            "watch_history": watch_history(user),
        },
    )
