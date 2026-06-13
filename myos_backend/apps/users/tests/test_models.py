from django.test import TestCase

from apps.users.models import CustomUser


class UserProfileTests(TestCase):
    def test_profile_created_with_user(self):
        user = CustomUser.objects.create_user(
            email="profile@example.com",
            password="test-password-123",
            first_name="Profile",
            last_name="User",
        )
        self.assertTrue(hasattr(user, "profile"))

    def test_avatar_initials_and_display_name(self):
        user = CustomUser.objects.create_user(
            email="initials@example.com",
            password="test-password-123",
            first_name="Ada",
            last_name="Lovelace",
        )
        self.assertEqual(user.avatar_initials, "AL")
        self.assertEqual(user.display_name, "Ada Lovelace")
