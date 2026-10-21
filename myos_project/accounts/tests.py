from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from myos_app.models import UserProfile


class SignupFlowTests(TestCase):
    def test_signup_page_and_login_link_render(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")
        self.assertContains(response, reverse("accounts:login"))

    def test_authenticated_user_still_reaches_signup_page(self):
        user = get_user_model().objects.create_user(
            email="already-here@example.com", username="already_here", password="S7!fR0ck-91-Tree",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")
        self.assertContains(response, "already-here@example.com")

    def test_login_entry_links_to_signup(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("accounts:signup"))

    def test_signup_persists_user_profile_and_logs_user_in(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "username": "ada_lovelace",
                "email": "ada@example.com",
                "password1": "S7!fR0ck-91-Tree",
                "password2": "S7!fR0ck-91-Tree",
            },
        )

        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        user = get_user_model().objects.get(email="ada@example.com")
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.display_name, "Ada Lovelace")
        self.assertEqual(profile.email, user.email)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

        dashboard = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard, 'data-authenticated="1"')
        self.assertContains(dashboard, reverse("accounts:signup"))
