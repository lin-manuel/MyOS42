from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Budget, FinanceEntry, SavingsGoal
from .permissions import FinancePermission
from .serializers import BudgetSerializer, FinanceEntrySerializer, SavingsGoalSerializer


class FinanceEntryViewSet(viewsets.ModelViewSet):
    serializer_class = FinanceEntrySerializer
    permission_classes = [IsAuthenticated, FinancePermission]
    filterset_fields = ("type", "account", "date")
    ordering_fields = ("date", "amount", "created_at")

    def get_queryset(self):
        return FinanceEntry.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated, FinancePermission]
    filterset_fields = ("category",)
    search_fields = ("category",)
    ordering_fields = ("category", "monthly_limit", "spent", "created_at")

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SavingsGoalViewSet(viewsets.ModelViewSet):
    serializer_class = SavingsGoalSerializer
    permission_classes = [IsAuthenticated, FinancePermission]
    search_fields = ("goal_name",)
    ordering_fields = ("deadline", "target_amount", "current_amount", "created_at")

    def get_queryset(self):
        return SavingsGoal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
