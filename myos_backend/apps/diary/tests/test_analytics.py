from datetime import date

from django.test import TestCase

from apps.diary.analytics import writing_streak
from apps.diary.models import DiaryEntry
from apps.users.models import CustomUser


class DiaryAnalyticsTests(TestCase):
    def test_writing_streak(self):
        user = CustomUser.objects.create_user(
            email="diary@example.com",
            password="test-password-123",
            first_name="Diary",
            last_name="User",
        )
        DiaryEntry.objects.create(user=user, title="Entry", date=date.today(), content="Hello")
        self.assertGreaterEqual(writing_streak(user), 1)
