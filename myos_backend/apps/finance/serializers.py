from rest_framework import serializers

from .models import Budget, FinanceEntry, SavingsGoal


class FinanceEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceEntry
        fields = (
            "id",
            "user",
            "type",
            "amount",
            "account",
            "category",
            "description",
            "date",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")


class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ("id", "user", "category", "monthly_limit", "spent", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at")


class SavingsGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsGoal
        fields = (
            "id",
            "user",
            "goal_name",
            "target_amount",
            "current_amount",
            "deadline",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")
