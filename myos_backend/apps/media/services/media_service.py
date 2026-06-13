from django.db.models import Prefetch

from apps.media.models import MediaItem, MediaProgress


PROGRESS_PREFETCH = Prefetch("progress_entries", queryset=MediaProgress.objects.order_by("-watched_at", "-id"))


class MediaService:
    @staticmethod
    def with_progress(user):
        return MediaItem.objects.filter(user=user).prefetch_related(PROGRESS_PREFETCH)

    @staticmethod
    def latest_progress(item):
        cached = getattr(item, "_prefetched_objects_cache", {})
        if "progress_entries" in cached:
            entries = cached["progress_entries"]
            return entries[0] if entries else None
        return item.progress_entries.order_by("-watched_at", "-id").first()

    @staticmethod
    def calculate_watch_time(items):
        total_minutes = 0
        for item in items:
            latest = MediaService.latest_progress(item)
            if item.type == MediaItem.TYPE_MOVIE:
                if item.status == MediaItem.STATUS_COMPLETED:
                    total_minutes += item.duration or 0
            else:
                watched = latest.episodes_watched if latest else 0
                total_minutes += watched * (item.episode_duration or 0)
        return {"minutes": total_minutes, "hours": round(total_minutes / 60, 2)}

    @staticmethod
    def calculate_completion_rate(items):
        rows = list(items)
        if not rows:
            return 0.0
        completed = len([item for item in rows if item.status == MediaItem.STATUS_COMPLETED])
        return round((completed / len(rows)) * 100, 2)

    @staticmethod
    def sync_media_status(progress):
        item = progress.media_item
        if progress.completed:
            item.status = MediaItem.STATUS_COMPLETED
        elif progress.episodes_watched > 0:
            item.status = MediaItem.STATUS_WATCHING
        item.save(update_fields=["status", "updated_at"])
        return item
