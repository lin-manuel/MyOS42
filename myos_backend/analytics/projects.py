from analytics.cache import cache_metric
from apps.projects.analytics import project_progress, task_completion_rate


def project_metrics(user):
    return cache_metric(
        "projects",
        user,
        lambda: {
            "projects": project_progress(user),
            "tasks": task_completion_rate(user),
        },
    )
