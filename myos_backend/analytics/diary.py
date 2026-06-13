from analytics.cache import cache_metric
from apps.diary.analytics import mood_trends, writing_streak


def diary_metrics(user):
    return cache_metric(
        "diary",
        user,
        lambda: {
            "mood_trends": mood_trends(user),
            "writing_streak": writing_streak(user),
        },
    )
