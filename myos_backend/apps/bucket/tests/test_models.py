from django.test import TestCase

from apps.bucket.models import BucketCategory, BucketItem
from apps.users.models import CustomUser


class BucketModelTests(TestCase):
    def test_user_gets_default_bucket_categories(self):
        user = CustomUser.objects.create_user(
            email="default-bucket@example.com",
            password="test-password-123",
            first_name="Bucket",
            last_name="Defaults",
        )
        categories = list(BucketCategory.objects.filter(user=user).values_list("name", flat=True))
        self.assertEqual(
            categories,
            ["Achievements", "Experiences", "Learning", "Travel", "Wealth"],
        )

    def test_category_counts_sync_on_item_changes(self):
        user = CustomUser.objects.create_user(
            email="bucket-counts@example.com",
            password="test-password-123",
            first_name="Bucket",
            last_name="Counts",
        )
        category = BucketCategory.objects.get(user=user, name="Travel")
        item = BucketItem.objects.create(
            user=user,
            category=category,
            title="Visit Japan",
            starred=True,
            status=BucketItem.STATUS_IDEA,
        )
        category.refresh_from_db()
        self.assertEqual(category.item_count, 1)
        self.assertEqual(category.completed_count, 0)

        item.status = BucketItem.STATUS_COMPLETED
        item.save()
        category.refresh_from_db()
        self.assertEqual(category.completed_count, 1)
