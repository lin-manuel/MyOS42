from django.db.models import Count

from .models import Project, Task


def project_progress(user):
    return list(Project.objects.filter(user=user).values("id", "title", "progress", "status", "priority"))


def task_completion_rate(user):
    total = Task.objects.filter(project__user=user).count()
    completed = Task.objects.filter(project__user=user, status=Task.STATUS_COMPLETED).count()
    status_totals = list(
        Task.objects.filter(project__user=user).values("status").annotate(total=Count("id")).order_by("status")
    )
    return {
        "total": total,
        "completed": completed,
        "completion_rate": round((completed / total) * 100, 2) if total else 0.0,
        "status_totals": status_totals,
    }
