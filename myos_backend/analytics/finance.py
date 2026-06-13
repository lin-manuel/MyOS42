from analytics.cache import cache_metric
from apps.finance.analytics import income_vs_expense, monthly_spending, savings_rate
from apps.finance.services.finance_service import FinanceService


def finance_metrics(user):
    return cache_metric(
        "finance",
        user,
        lambda: {
            "summary": income_vs_expense(user),
            "monthly_spending": monthly_spending(user),
            "savings_rate": savings_rate(user),
            "budgets": FinanceService.budget_health(user),
            "savings_goals": FinanceService.savings_progress(user),
        },
    )
