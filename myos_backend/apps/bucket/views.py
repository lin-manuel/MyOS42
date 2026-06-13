from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from .models import BucketCategory, BucketItem
from .permissions import BucketPermission
from .serializers import BucketCategorySerializer, BucketItemSerializer


class BucketCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = BucketCategorySerializer
    permission_classes = [IsAuthenticated, BucketPermission]
    filterset_fields = ("name",)
    search_fields = ("name",)
    ordering_fields = ("name", "created_at", "item_count", "completed_count")

    def get_queryset(self):
        return BucketCategory.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BucketItemViewSet(viewsets.ModelViewSet):
    serializer_class = BucketItemSerializer
    permission_classes = [IsAuthenticated, BucketPermission]
    filterset_fields = ("status", "starred", "category")
    search_fields = ("title", "description")
    ordering_fields = ("created_at", "target_date", "title", "status")

    def get_queryset(self):
        return BucketItem.objects.select_related("category").filter(user=self.request.user)

    def perform_create(self, serializer):
        category = serializer.validated_data["category"]
        if category.user != self.request.user:
            raise PermissionDenied("Cannot add items to another user's category")
        serializer.save(user=self.request.user)
