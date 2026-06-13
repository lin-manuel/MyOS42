from django.db.models import Count, Sum

from .models import EducationRecord, Scholarship


def education_timeline(user):
    return list(EducationRecord.objects.filter(user=user).values("level", "institution", "start_year", "end_year"))


def scholarship_progress(user):
    by_status = list(
        Scholarship.objects.filter(user=user).values("status").annotate(total=Count("id")).order_by("status")
    )
    study_hours = EducationRecord.objects.filter(user=user).aggregate(total=Sum("study_hours"))["total"] or 0
    return {"by_status": by_status, "study_hours": study_hours}
