from rest_framework import serializers

from .models import Project, ProjectAttachment, ProjectNote, Task


class ProjectSerializer(serializers.ModelSerializer):
    task_total = serializers.IntegerField(read_only=True)
    task_completed = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = (
            "id",
            "user",
            "title",
            "description",
            "status",
            "priority",
            "progress",
            "start_date",
            "deadline",
            "is_archived",
            "metadata",
            "task_total",
            "task_completed",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "created_at", "updated_at")


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            "id",
            "project",
            "title",
            "description",
            "status",
            "due_date",
            "priority",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "completed_at", "created_at", "updated_at")


class ProjectNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectNote
        fields = ("id", "project", "content", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class ProjectAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectAttachment
        fields = ("id", "user", "project", "title", "file", "notes", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at")
