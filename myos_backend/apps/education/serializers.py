from rest_framework import serializers

from .models import EducationDocument, EducationRecord, Scholarship


class EducationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationRecord
        fields = (
            "id",
            "user",
            "level",
            "institution",
            "start_year",
            "end_year",
            "grade",
            "study_hours",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")


class ScholarshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scholarship
        fields = ("id", "user", "name", "country", "deadline", "status", "notes", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at")


class EducationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationDocument
        fields = (
            "id",
            "user",
            "title",
            "document_type",
            "version",
            "file",
            "expires_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")
