from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.common.fields import EncryptedTextField
from apps.common.models import TimeStampedModel


class FinanceEntry(TimeStampedModel):
    TYPE_INCOME = "income"
    TYPE_EXPENSE = "expense"
    TYPE_SAVINGS = "savings"

    TYPE_CHOICES = (
        (TYPE_INCOME, "Income"),
        (TYPE_EXPENSE, "Expense"),
        (TYPE_SAVINGS, "Savings"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="finance_entries")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    account = models.CharField(max_length=120, blank=True, default="")
    category = EncryptedTextField()
    description = EncryptedTextField(blank=True, default="")
    date = models.DateField()

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.user_id} {self.type} {self.amount}"


class Budget(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets")
    category = models.CharField(max_length=120)
    monthly_limit = models.DecimalField(max_digits=12, decimal_places=2)
    spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["category"]

    def __str__(self):
        return f"{self.category}:{self.monthly_limit}"


class SavingsGoal(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="savings_goals")
    goal_name = models.CharField(max_length=180)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deadline = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["deadline", "goal_name"]

    def __str__(self):
        return self.goal_name
