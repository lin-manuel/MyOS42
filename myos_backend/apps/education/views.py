from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import EducationDocument, EducationRecord, Scholarship
from .permissions import EducationPermission
from .serializers import EducationDocumentSerializer, EducationRecordSerializer, ScholarshipSerializer


class EducationRecordViewSet(viewsets.ModelViewSet):
    serializer_class = EducationRecordSerializer
    permission_classes = [IsAuthenticated, EducationPermission]
    search_fields = ("level", "institution", "grade")
    ordering_fields = ("start_year", "end_year", "created_at")

    def get_queryset(self):
        return EducationRecord.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ScholarshipViewSet(viewsets.ModelViewSet):
    serializer_class = ScholarshipSerializer
    permission_classes = [IsAuthenticated, EducationPermission]
    filterset_fields = ("status", "country")
    search_fields = ("name", "country", "notes")
    ordering_fields = ("deadline", "created_at", "name")

    def get_queryset(self):
        return Scholarship.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EducationDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = EducationDocumentSerializer
    permission_classes = [IsAuthenticated, EducationPermission]
    filterset_fields = ("document_type",)
    search_fields = ("title", "document_type", "version")
    ordering_fields = ("created_at", "title")

    def get_queryset(self):
        return EducationDocument.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
