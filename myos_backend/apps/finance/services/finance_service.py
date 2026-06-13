from django.db.models import Sum
from django.db.models.functions import TruncMonth

from apps.finance.models import Budget, FinanceEntry, SavingsGoal


class FinanceService:
    @staticmethod
    def summary_for_user(user):
        qs = FinanceEntry.objects.filter(user=user)
        income = qs.filter(type=FinanceEntry.TYPE_INCOME).aggregate(total=Sum("amount"))["total"] or 0
        expense = qs.filter(type=FinanceEntry.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"] or 0
        savings = qs.filter(type=FinanceEntry.TYPE_SAVINGS).aggregate(total=Sum("amount"))["total"] or 0
        return {
            "income": income,
            "expense": expense,
            "savings": savings,
            "net": income - expense,
        }

    @staticmethod
    def monthly_spending(user):
        rows = (
            FinanceEntry.objects.filter(user=user, type=FinanceEntry.TYPE_EXPENSE)
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        return [
            {"month": row["month"].strftime("%Y-%m") if row["month"] else "", "total": float(row["total"] or 0)}
            for row in rows
        ]

    @staticmethod
    def savings_progress(user):
        return list(SavingsGoal.objects.filter(user=user).values("goal_name", "target_amount", "current_amount", "deadline"))

    @staticmethod
    def budget_health(user):
        return list(Budget.objects.filter(user=user).values("category", "monthly_limit", "spent"))
