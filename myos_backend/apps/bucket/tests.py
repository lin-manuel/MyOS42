from datetime import date

from django.test import TestCase

from apps.bucket.analytics import goals_per_year
from apps.bucket.models import BucketCategory, BucketItem
from apps.users.models import CustomUser


class BucketAnalyticsTests(TestCase):
    def test_goals_per_year(self):
        user = CustomUser.objects.create_user(
            email="bucket@example.com",
            password="test-password-123",
            first_name="Bucket",
            last_name="User",
        )
        category = BucketCategory.objects.get(user=user, name="Travel")
        BucketItem.objects.create(user=user, category=category, title="Visit Japan", target_date=date(2026, 7, 1))
        self.assertEqual(goals_per_year(user)[0]["year"], 2026)
