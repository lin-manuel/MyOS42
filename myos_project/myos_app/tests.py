import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from .models import (
    BucketGoal,
    Budget,
    Category,
    DiaryEntry,
    DigitalAccounts,
    IdentityDocuments,
    PageFormData,
    Project,
    Task,
    Transaction,
)


class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_loads(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_bootstrap_returns_json(self):
        response = self.client.get(reverse("bootstrap_data"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("tasks", data)
        self.assertIn("diary_entries", data)


class TaskAPITests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_create_task(self):
        response = self.client.post(
            reverse("create_task"),
            data=json.dumps({"title": "Test task", "priority": "high"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["task"]["title"], "Test task")

    def test_create_task_missing_title(self):
        response = self.client.post(
            reverse("create_task"),
            data=json.dumps({"priority": "medium"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_toggle_task(self):
        task = Task.objects.create(title="Toggle me", sort_order=1)
        response = self.client.post(reverse("toggle_task", args=[task.id]))
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertTrue(task.is_done)


class DiaryAPITests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_save_diary_entry(self):
        response = self.client.post(
            reverse("save_diary_entry"),
            data=json.dumps({"content": "Today was productive", "mood": "happy"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(DiaryEntry.objects.count(), 1)

    def test_diary_streak(self):
        DiaryEntry.objects.create(entry_date=date.today(), mood="good", content="Test")
        response = self.client.get(reverse("diary_streak"))
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["current_streak"], 1)


class GlobalSearchTests(TestCase):
    def setUp(self):
        self.client = Client()
        Task.objects.create(title="Write scholarship essay", sort_order=1)
        DiaryEntry.objects.create(
            entry_date=date.today(),
            mood="focused",
            content="Working on scholarship applications today",
        )

    def test_search_finds_task(self):
        response = self.client.get(reverse("global_search"), {"q": "scholarship"})
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertTrue(any(result["type"] == "task" for result in data["results"]))

    def test_search_requires_min_chars(self):
        response = self.client.get(reverse("global_search"), {"q": "a"})
        data = response.json()
        self.assertEqual(data["results"], [])


class BucketGoalTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_create_bucket_goal(self):
        self.client.post(
            reverse("add_bucket_goal"),
            data={"title": "Visit Japan", "category": "travel", "target_year": "2027"},
        )
        self.assertEqual(BucketGoal.objects.count(), 1)


class FinanceModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Living",
            slug="living-test",
            kind=Category.KIND_EXPENSE,
            color="#8B5A2B",
            icon="fa-house",
        )

    def test_transaction_amount_must_be_positive(self):
        tx = Transaction(
            tx_date=date.today(),
            description="Invalid amount",
            category=self.category,
            account=Transaction.ACCOUNT_BANK,
            tx_type=Transaction.TYPE_EXPENSE,
            amount=Decimal("-5.00"),
        )
        with self.assertRaises(ValidationError):
            tx.full_clean()

    def test_budget_unique_per_category_and_month(self):
        month_start = date.today().replace(day=1)
        Budget.objects.create(category=self.category, period_start=month_start, monthly_limit=Decimal("1000.00"))
        with self.assertRaises(IntegrityError):
            Budget.objects.create(category=self.category, period_start=month_start, monthly_limit=Decimal("2000.00"))


class FinanceApiTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_finance_bootstrap_is_accessible(self):
        response = self.client.get(reverse("finance_bootstrap"))
        self.assertEqual(response.status_code, 200)

    def test_finance_bootstrap_returns_expected_sections(self):
        response = self.client.get(reverse("finance_bootstrap"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertGreaterEqual(len(payload.get("metrics", [])), 9)
        self.assertIn("ledger", payload)
        self.assertIn("charts", payload)
        self.assertIn("alerts", payload)
        self.assertIn("insights", payload)

    def test_csv_export_uses_filters(self):
        category = Category.objects.create(
            name="CSV Category",
            slug="csv-category",
            kind=Category.KIND_EXPENSE,
            color="#8B5A2B",
            icon="fa-tag",
        )

        Transaction.objects.create(
            tx_date=date.today(),
            description="CSV Match Item",
            category=category,
            account=Transaction.ACCOUNT_BANK,
            tx_type=Transaction.TYPE_EXPENSE,
            amount=Decimal("123.00"),
        )
        Transaction.objects.create(
            tx_date=date.today(),
            description="CSV Other Item",
            category=category,
            account=Transaction.ACCOUNT_BANK,
            tx_type=Transaction.TYPE_EXPENSE,
            amount=Decimal("77.00"),
        )

        response = self.client.get(reverse("finance_transactions_export_csv"), {"q": "Match"})
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("CSV Match Item", content)
        self.assertNotIn("CSV Other Item", content)


class EducationApiTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_education_bootstrap_is_accessible(self):
        response = self.client.get(reverse("education_bootstrap"))
        self.assertEqual(response.status_code, 200)

    def test_education_bootstrap_returns_sections(self):
        response = self.client.get(reverse("education_bootstrap"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("ok"))
        self.assertIn("academic_levels", payload)
        self.assertIn("documents", payload)
        self.assertIn("scholarships", payload)
        self.assertIn("deadline_alerts", payload)

    def test_document_create_and_scholarship_create(self):
        self.client.get(reverse("education_bootstrap"))

        sample = SimpleUploadedFile("statement.pdf", b"fake-pdf-content", content_type="application/pdf")
        response = self.client.post(
            reverse("education_documents_create"),
            data={
                "title": "Personal Statement",
                "document_type": "personal_statement",
                "version": "v1",
                "notes": "Draft",
                "file": sample,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json().get("ok"))

        response2 = self.client.post(
            reverse("education_scholarships_create"),
            data=json.dumps(
                {
                    "name": "Test Scholarship",
                    "country": "Germany",
                    "field_of_study": "Engineering",
                    "degree_level": "Masters",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response2.status_code, 201)
        self.assertTrue(response2.json().get("ok"))


class PersonalVaultApiTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_personal_vault_bootstrap_is_accessible(self):
        response = self.client.get(reverse("personal_vault_bootstrap"))
        self.assertEqual(response.status_code, 200)

    def test_step3_encryption_and_bootstrap_roundtrip(self):
        payload = {
            "national_id": "12345678",
            "passport_number": "A1234567",
            "passport_expiry": "2030-12-31",
            "drivers_license": "DL-7777",
            "student_id": "ST-1001",
        }
        response = self.client.post(
            reverse("personal_vault_step3_save"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        docs = IdentityDocuments.objects.first()
        self.assertIsNotNone(docs)
        self.assertNotEqual(docs.national_id_encrypted, payload["national_id"])
        self.assertNotEqual(docs.passport_number_encrypted, payload["passport_number"])
        self.assertTrue(docs.national_id_encrypted)
        self.assertTrue(docs.passport_number_encrypted)

        bootstrap = self.client.get(reverse("personal_vault_bootstrap"))
        self.assertEqual(bootstrap.status_code, 200)
        identity_docs = bootstrap.json().get("identity_documents", {})
        self.assertEqual(identity_docs.get("national_id"), payload["national_id"])
        self.assertEqual(identity_docs.get("passport_number"), payload["passport_number"])

    def test_digital_account_crud(self):
        create_response = self.client.post(
            reverse("personal_vault_digital_accounts_create"),
            data=json.dumps(
                {
                    "platform": "github",
                    "custom_platform": "",
                    "username": "immanuel",
                    "email_used": "immanuel@example.com",
                    "profile_link": "https://github.com/immanuel",
                    "notes": "Main dev profile",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        account_id = create_response.json()["account"]["id"]
        self.assertEqual(DigitalAccounts.objects.count(), 1)

        update_response = self.client.post(
            reverse("personal_vault_digital_accounts_update", kwargs={"account_id": account_id}),
            data=json.dumps(
                {
                    "platform": "github",
                    "custom_platform": "",
                    "username": "immanuel-updated",
                    "email_used": "immanuel@example.com",
                    "profile_link": "https://github.com/immanuel-updated",
                    "notes": "Updated",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["account"]["username"], "immanuel-updated")

        list_response = self.client.get(reverse("personal_vault_digital_accounts"))
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json().get("rows", [])), 1)

        delete_response = self.client.post(
            reverse("personal_vault_digital_accounts_delete", kwargs={"account_id": account_id}),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(DigitalAccounts.objects.count(), 0)

    def test_identity_file_upload_rejects_invalid_type(self):
        bad_file = SimpleUploadedFile("secret.exe", b"MZ-binary", content_type="application/octet-stream")
        response = self.client.post(
            reverse("personal_vault_identity_file_upload"),
            data={
                "file_type": "other",
                "file": bad_file,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", response.json().get("error", ""))


class ProjectsApiTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_page_render_sets_csrf_cookie(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.get(reverse("education"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", csrf_client.cookies)

    def test_project_crud(self):
        create_response = self.client.post(
            reverse("projects_create"),
            data=json.dumps(
                {
                    "title": "Build MVP",
                    "description": "First production-ready release",
                    "status": "in_progress",
                    "progress": 35,
                    "start_date": "2026-03-01",
                    "end_date": "2026-06-30",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertTrue(create_response.json().get("ok"))
        project_id = create_response.json()["project"]["id"]
        self.assertEqual(Project.objects.count(), 1)

        list_response = self.client.get(reverse("projects_list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json().get("rows", [])), 1)

        update_response = self.client.post(
            reverse("projects_update", kwargs={"project_id": project_id}),
            data=json.dumps(
                {
                    "title": "Build MVP v2",
                    "status": "completed",
                    "progress": 100,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["project"]["status"], "completed")
        self.assertEqual(update_response.json()["project"]["progress"], 100)

        delete_response = self.client.post(
            reverse("projects_delete", kwargs={"project_id": project_id}),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(Project.objects.count(), 0)


class HtmxPageRenderingTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_full_page_keeps_shell_and_compiled_assets(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'css/tailwind.min.css')
        self.assertContains(response, 'https://unpkg.com/htmx.org@1.9.12')
        self.assertContains(response, 'id="main-content-swap"', html=False)
        self.assertNotContains(response, 'https://cdn.tailwindcss.com')
        self.assertContains(response, 'id="page-dashboard"', html=False)
        self.assertContains(response, 'class="sidebar"', html=False)

    def test_dashboard_htmx_request_returns_partial_without_shell(self):
        response = self.client.get(reverse("dashboard"), HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="page-dashboard"', html=False)
        self.assertContains(response, 'data-page-key="dashboard"', html=False)
        self.assertNotContains(response, '<html', html=False)
        self.assertNotContains(response, 'class="sidebar"', html=False)


class NotificationCachingTests(TestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user_a = user_model.objects.create_user(
            email="alpha@example.com",
            password="password123",
            username="alpha",
            first_name="Alpha",
            last_name="User",
        )
        self.user_b = user_model.objects.create_user(
            email="bravo@example.com",
            password="password123",
            username="bravo",
            first_name="Bravo",
            last_name="User",
        )
        self.task = Task.objects.create(title="Renew passport", sort_order=1)
        PageFormData.objects.create(
            page_slug="reminders_hub_data",
            data={
                "reminders": [],
                "task_meta": {
                    str(self.task.id): {
                        "due_date": (date.today() + timedelta(days=1)).isoformat(),
                    }
                },
            },
        )
        self.task.refresh_from_db()
        self.notification_id = f"task-{self.task.id}-{self.task.updated_at.strftime('%Y%m%d%H%M%S')}"

    def test_notification_reads_are_cached_per_user_and_invalidate_immediately(self):
        client_a = Client()
        client_b = Client()
        client_a.force_login(self.user_a)
        client_b.force_login(self.user_b)

        first_feed = client_a.get(reverse("notifications_feed"))
        self.assertEqual(first_feed.status_code, 200)
        self.assertEqual(first_feed.json()["summary"]["unread_count"], 1)

        mark_response = client_a.post(reverse("notifications_mark_read", args=[self.notification_id]))
        self.assertEqual(mark_response.status_code, 200)

        second_feed = client_a.get(reverse("notifications_feed"))
        self.assertEqual(second_feed.status_code, 200)
        self.assertEqual(second_feed.json()["summary"]["unread_count"], 0)

        other_user_feed = client_b.get(reverse("notifications_feed"))
        self.assertEqual(other_user_feed.status_code, 200)
        self.assertEqual(other_user_feed.json()["summary"]["unread_count"], 1)
