from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.common.services import FileSecurityService

from .models import Episode, MediaItem, MediaProgress, Season
from .permissions import MediaPermission
from .serializers import EpisodeSerializer, MediaItemSerializer, MediaProgressSerializer, SeasonSerializer


class MediaItemViewSet(viewsets.ModelViewSet):
    serializer_class = MediaItemSerializer
    permission_classes = [IsAuthenticated, MediaPermission]
    filterset_fields = ("category", "type", "status", "platform", "year")
    search_fields = ("title", "description", "genre", "studio", "platform", "country")
    ordering_fields = ("date_added", "year", "title")

    def get_queryset(self):
        return MediaItem.objects.filter(user=self.request.user).prefetch_related("progress_entries")

    def _validate_media_uploads(self, serializer):
        for field_name in ("cover_image", "source_file"):
            uploaded_file = serializer.validated_data.get(field_name)
            if uploaded_file is not None:
                scan_result = FileSecurityService.scan(uploaded_file)
                if scan_result.get("status") != "clean":
                    raise PermissionDenied(f"{field_name} did not pass validation")

    def perform_create(self, serializer):
        self._validate_media_uploads(serializer)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        self._validate_media_uploads(serializer)
        serializer.save()


class MediaProgressViewSet(viewsets.ModelViewSet):
    serializer_class = MediaProgressSerializer
    permission_classes = [IsAuthenticated, MediaPermission]
    filterset_fields = ("completed", "media_item")
    ordering_fields = ("watched_at", "episodes_watched", "rating")

    def get_queryset(self):
        return MediaProgress.objects.filter(media_item__user=self.request.user).select_related("media_item")


class SeasonViewSet(viewsets.ModelViewSet):
    serializer_class = SeasonSerializer
    permission_classes = [IsAuthenticated, MediaPermission]
    filterset_fields = ("media_item",)
    ordering_fields = ("number", "created_at")

    def get_queryset(self):
        return Season.objects.filter(media_item__user=self.request.user).select_related("media_item")


class EpisodeViewSet(viewsets.ModelViewSet):
    serializer_class = EpisodeSerializer
    permission_classes = [IsAuthenticated, MediaPermission]
    filterset_fields = ("season",)
    search_fields = ("title", "season__media_item__title")
    ordering_fields = ("number", "air_date", "duration")

    def get_queryset(self):
        return Episode.objects.filter(season__media_item__user=self.request.user).select_related("season", "season__media_item")
