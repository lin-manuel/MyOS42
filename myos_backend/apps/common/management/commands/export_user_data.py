import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.diary.models import DiaryEntry
from apps.education.models import EducationDocument, EducationRecord, Scholarship
from apps.finance.models import Budget, FinanceEntry, SavingsGoal
from apps.media.models import MediaItem, MediaProgress
from apps.projects.models import Project, ProjectNote, Task


class Command(BaseCommand):
    help = "Export a user's MyOS data as JSON."

    def add_arguments(self, parser):
        parser.add_argument("email")

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(email=options["email"]).first()
        if not user:
            raise CommandError("User not found")

        payload = {
            "user": {"email": user.email, "first_name": user.first_name, "last_name": user.last_name},
            "projects": list(Project.objects.filter(user=user).values()),
            "tasks": list(Task.objects.filter(project__user=user).values()),
            "project_notes": list(ProjectNote.objects.filter(project__user=user).values()),
            "finance_entries": list(FinanceEntry.objects.filter(user=user).values()),
            "budgets": list(Budget.objects.filter(user=user).values()),
            "savings_goals": list(SavingsGoal.objects.filter(user=user).values()),
            "education_records": list(EducationRecord.objects.filter(user=user).values()),
            "scholarships": list(Scholarship.objects.filter(user=user).values()),
            "education_documents": list(EducationDocument.objects.filter(user=user).values()),
            "diary": list(DiaryEntry.objects.filter(user=user).values()),
            "media": list(MediaItem.objects.filter(user=user).values()),
            "media_progress": list(MediaProgress.objects.filter(media_item__user=user).values()),
        }
        self.stdout.write(json.dumps(payload, indent=2, default=str))
