from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.finance.analytics import savings_rate
from apps.finance.models import FinanceEntry
from apps.users.models import CustomUser


class FinanceAnalyticsTests(TestCase):
    def test_savings_rate(self):
        user = CustomUser.objects.create_user(
            email="finance@example.com",
            password="test-password-123",
            first_name="Finance",
            last_name="User",
        )
        FinanceEntry.objects.create(
            user=user,
            type=FinanceEntry.TYPE_INCOME,
            amount=Decimal("1000.00"),
            category="Salary",
            date=date(2026, 1, 1),
        )
        FinanceEntry.objects.create(
            user=user,
            type=FinanceEntry.TYPE_SAVINGS,
            amount=Decimal("250.00"),
            category="Savings",
            date=date(2026, 1, 2),
        )
        self.assertEqual(savings_rate(user), 25.0)
