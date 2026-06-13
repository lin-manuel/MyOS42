from django.db.models import Sum

from .models import EducationRecord, Scholarship


class EducationService:
    @staticmethod
    def study_summary(user):
        total_hours = EducationRecord.objects.filter(user=user).aggregate(total=Sum("study_hours"))["total"] or 0
        scholarship_total = Scholarship.objects.filter(user=user).count()
        scholarship_applied = Scholarship.objects.filter(user=user, status=Scholarship.STATUS_APPLIED).count()
        return {
            "study_hours": total_hours,
            "scholarship_total": scholarship_total,
            "scholarship_applied": scholarship_applied,
        }
