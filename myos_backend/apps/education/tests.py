from datetime import date

from django.test import TestCase

from apps.education.analytics import scholarship_progress
from apps.education.models import EducationRecord, Scholarship
from apps.users.models import CustomUser


class EducationAnalyticsTests(TestCase):
    def test_scholarship_progress(self):
        user = CustomUser.objects.create_user(
            email="education@example.com",
            password="test-password-123",
            first_name="Edu",
            last_name="User",
        )
        EducationRecord.objects.create(
            user=user,
            level="Bachelor",
            institution="Example University",
            start_year=2023,
            study_hours=120,
        )
        Scholarship.objects.create(
            user=user,
            name="Global Scholars",
            country="Canada",
            deadline=date(2026, 6, 1),
            status=Scholarship.STATUS_APPLIED,
        )
        payload = scholarship_progress(user)
        self.assertEqual(payload["study_hours"], 120)
        self.assertEqual(payload["by_status"][0]["total"], 1)
