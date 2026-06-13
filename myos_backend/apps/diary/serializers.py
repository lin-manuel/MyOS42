from rest_framework import serializers
from .models import DiaryEntry


class DiaryEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = DiaryEntry
        fields = (
            "id",
            "user",
            "title",
            "date",
            "content",
            "mood",
            "tags",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")
