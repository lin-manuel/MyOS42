from rest_framework import serializers
from .models import BucketCategory, BucketItem


class BucketCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BucketCategory
        fields = ("id", "user", "name", "icon", "color", "item_count", "completed_count", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at")


class BucketItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BucketItem
        fields = (
            "id",
            "user",
            "category",
            "title",
            "description",
            "starred",
            "status",
            "target_date",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")
