from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.common.services import FileSecurityService

from .models import Project, ProjectAttachment, ProjectNote, Task
from .permissions import ProjectPermission
from .serializers import ProjectAttachmentSerializer, ProjectNoteSerializer, ProjectSerializer, TaskSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, ProjectPermission]
    filterset_fields = ("status", "priority", "is_archived")
    search_fields = ("title", "description")
    ordering_fields = ("created_at", "deadline", "progress", "title")

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user).annotate(
            task_total=Count("tasks"),
            task_completed=Count("tasks", filter=Q(tasks__status=Task.STATUS_COMPLETED)),
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, ProjectPermission]
    filterset_fields = ("status", "priority", "project")
    search_fields = ("title", "description", "project__title")
    ordering_fields = ("created_at", "due_date", "priority", "status", "title")

    def get_queryset(self):
        return Task.objects.filter(project__user=self.request.user).select_related("project")


class ProjectNoteViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectNoteSerializer
    permission_classes = [IsAuthenticated, ProjectPermission]
    search_fields = ("content", "project__title")
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        return ProjectNote.objects.filter(project__user=self.request.user).select_related("project")


class ProjectAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectAttachmentSerializer
    permission_classes = [IsAuthenticated, ProjectPermission]
    filterset_fields = ("project",)
    search_fields = ("title", "notes", "project__title")
    ordering_fields = ("created_at", "title")

    def get_queryset(self):
        return ProjectAttachment.objects.filter(user=self.request.user).select_related("project")

    def _validate_attachment_payload(self, serializer):
        project = serializer.validated_data["project"]
        if project.user != self.request.user:
            raise PermissionDenied("Cannot attach files to another user's project")
        uploaded_file = serializer.validated_data.get("file")
        if uploaded_file is not None:
            scan_result = FileSecurityService.scan(uploaded_file)
            if scan_result.get("status") != "clean":
                raise PermissionDenied("Uploaded file did not pass validation")

    def perform_create(self, serializer):
        self._validate_attachment_payload(serializer)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        self._validate_attachment_payload(serializer)
        serializer.save()
