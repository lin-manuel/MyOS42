from .services.finance_service import FinanceService


def income_vs_expense(user):
    return FinanceService.summary_for_user(user)


def monthly_spending(user):
    return FinanceService.monthly_spending(user)


def savings_rate(user):
    summary = FinanceService.summary_for_user(user)
    income = float(summary["income"] or 0)
    savings = float(summary["savings"] or 0)
    return round((savings / income) * 100, 2) if income else 0.0
