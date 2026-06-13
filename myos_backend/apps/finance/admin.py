from django.contrib import admin

from .models import Budget, FinanceEntry, SavingsGoal


@admin.register(FinanceEntry)
class FinanceEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "amount", "account", "date", "created_at")
    list_filter = ("type", "date", "account")
    search_fields = ("user__email",)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "monthly_limit", "spent")
    search_fields = ("user__email", "category")


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ("user", "goal_name", "target_amount", "current_amount", "deadline")
    search_fields = ("user__email", "goal_name")
