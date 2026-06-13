from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import DiaryEntry
from .permissions import DiaryPermission
from .serializers import DiaryEntrySerializer


class DiaryEntryViewSet(viewsets.ModelViewSet):
    serializer_class = DiaryEntrySerializer
    permission_classes = [IsAuthenticated, DiaryPermission]
    filterset_fields = ("date", "mood")
    search_fields = ("title", "mood")
    ordering_fields = ("date", "created_at", "updated_at")

    def get_queryset(self):
        return DiaryEntry.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
