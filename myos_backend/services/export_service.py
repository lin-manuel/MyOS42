from apps.diary.models import DiaryEntry
from apps.education.models import EducationRecord, Scholarship
from apps.finance.models import FinanceEntry
from apps.media.models import MediaItem
from apps.projects.models import Project, Task


class AccountExportService:
    @staticmethod
    def export(user):
        return {
            "projects": list(Project.objects.filter(user=user).values()),
            "tasks": list(Task.objects.filter(project__user=user).values()),
            "finance": list(FinanceEntry.objects.filter(user=user).values()),
            "diary": list(DiaryEntry.objects.filter(user=user).values()),
            "media": list(MediaItem.objects.filter(user=user).values()),
            "education_records": list(EducationRecord.objects.filter(user=user).values()),
            "scholarships": list(Scholarship.objects.filter(user=user).values()),
        }
