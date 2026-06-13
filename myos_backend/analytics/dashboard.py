from analytics.cache import cache_metric
from analytics.bucket import bucket_metrics
from analytics.diary import diary_metrics
from analytics.education import education_metrics
from analytics.finance import finance_metrics
from analytics.media import media_metrics
from analytics.projects import project_metrics


def dashboard_metrics(user):
    return cache_metric(
        "dashboard",
        user,
        lambda: {
            "finance": finance_metrics(user),
            "projects": project_metrics(user),
            "education": education_metrics(user),
            "media": media_metrics(user),
            "bucket": bucket_metrics(user),
            "diary": diary_metrics(user),
        },
    )
