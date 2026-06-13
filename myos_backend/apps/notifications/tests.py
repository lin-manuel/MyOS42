from django.test import TestCase

from apps.notifications.services.notification_service import NotificationService
from apps.users.models import CustomUser


class NotificationServiceTests(TestCase):
    def test_create_notification(self):
        user = CustomUser.objects.create_user(
            email="notify@example.com",
            password="test-password-123",
            first_name="Notify",
            last_name="User",
        )
        notification = NotificationService.create(user, "Hello", category="system")
        self.assertEqual(notification.category, "system")
