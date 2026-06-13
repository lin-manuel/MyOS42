from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.api.services.dashboard_service import DashboardService
from apps.finance.models import FinanceEntry
from apps.notifications.models import Notification
from apps.projects.models import Project
from apps.users.models import CustomUser


class DashboardServiceTests(TestCase):
    def test_dashboard_payload_contains_module_sections(self):
        user = CustomUser.objects.create_user(
            email="dashboard@example.com",
            password="test-password-123",
            first_name="Dash",
            last_name="User",
        )
        Project.objects.create(user=user, title="Build MyOS")
        FinanceEntry.objects.create(
            user=user,
            type=FinanceEntry.TYPE_INCOME,
            amount=Decimal("500.00"),
            category="Salary",
            date=date(2026, 1, 1),
        )
        Notification.objects.create(user=user, message="Hello")

        payload = DashboardService.get_dashboard_payload(user)

        self.assertIn("finance", payload)
        self.assertIn("projects", payload)
        self.assertIn("events", payload)
        self.assertGreaterEqual(payload["unread_notifications"], 1)
