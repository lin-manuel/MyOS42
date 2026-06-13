from rest_framework import serializers

from .models import Episode, MediaItem, MediaProgress, Season


class MediaItemSerializer(serializers.ModelSerializer):
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = MediaItem
        fields = (
            "id",
            "user",
            "title",
            "description",
            "studio",
            "category",
            "type",
            "genre",
            "country",
            "platform",
            "cover_image",
            "source_file",
            "year",
            "duration",
            "total_seasons",
            "total_episodes",
            "episode_duration",
            "date_added",
            "status",
            "progress_percent",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "date_added", "created_at", "updated_at", "progress_percent")

    def get_progress_percent(self, obj):
        latest = obj.progress_entries.order_by("-watched_at", "-id").first()
        if obj.type == MediaItem.TYPE_MOVIE:
            return 100 if obj.status == MediaItem.STATUS_COMPLETED else 0
        total = obj.total_episodes or 0
        watched = latest.episodes_watched if latest else 0
        return int((watched / total) * 100) if total else 0


class MediaProgressSerializer(serializers.ModelSerializer):
    watch_time_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = MediaProgress
        fields = (
            "id",
            "media_item",
            "episodes_watched",
            "current_season",
            "current_episode",
            "completed",
            "rating",
            "notes",
            "watch_time_minutes",
            "watched_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "watch_time_minutes", "watched_at", "created_at", "updated_at")


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = ("id", "media_item", "number", "title", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class EpisodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Episode
        fields = ("id", "season", "number", "title", "duration", "air_date", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
