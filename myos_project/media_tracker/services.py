from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Prefetch

from .models import MediaItem, MediaProgress


PROGRESS_PREFETCH = Prefetch(
    "progress_entries",
    queryset=MediaProgress.objects.order_by("-date_watched", "-id"),
)


def _with_progress(queryset):
    if queryset is None:
        queryset = MediaItem.objects.all()
    return queryset.prefetch_related(PROGRESS_PREFETCH)


def _latest_progress(item):
    return item.latest_progress_entry()


def calculate_watch_time(media_items):
    total_minutes = 0
    for item in media_items:
        latest = _latest_progress(item)
        if item.type == MediaItem.MediaType.MOVIE:
            is_watched = item.status == MediaItem.Status.COMPLETED or bool(latest and latest.completed)
            if is_watched:
                total_minutes += item.duration or 0
            continue

        episodes_watched = latest.episodes_watched if latest else 0
        total_minutes += episodes_watched * (item.episode_duration or 0)

    total_hours = (Decimal(total_minutes) / Decimal(60)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "minutes": total_minutes,
        "hours": float(total_hours),
    }


def calculate_completion_rate(media_items):
    items = list(media_items)
    total = len(items)
    if total == 0:
        return 0.0
    completed = 0
    for item in items:
        latest = _latest_progress(item)
        if item.status == MediaItem.Status.COMPLETED or bool(latest and latest.completed):
            completed += 1
    return round((completed / total) * 100, 2)


def _stats_from_rows(rows):
    watch_time = calculate_watch_time(rows)
    total = len(rows)
    completed = len([item for item in rows if item.status == MediaItem.Status.COMPLETED])
    watching = len([item for item in rows if item.status == MediaItem.Status.WATCHING])
    planned = len([item for item in rows if item.status == MediaItem.Status.PLANNED])
    return {
        "total": total,
        "completed": completed,
        "watching": watching,
        "planned": planned,
        "completion_rate": calculate_completion_rate(rows),
        "watch_time_minutes": watch_time["minutes"],
        "watch_time_hours": watch_time["hours"],
    }


def get_movies_stats(queryset=None):
    if queryset is None:
        queryset = MediaItem.objects.filter(category=MediaItem.Category.MOVIE)
    rows = list(_with_progress(queryset))
    stats = _stats_from_rows(rows)
    stats.update(
        {
            "items": rows,
            "movie_count": len(rows),
        }
    )
    return stats


def get_series_stats(queryset=None):
    if queryset is None:
        queryset = MediaItem.objects.filter(category=MediaItem.Category.SERIES)
    rows = list(_with_progress(queryset))
    stats = _stats_from_rows(rows)
    stats.update(
        {
            "items": rows,
            "series_count": len(rows),
        }
    )
    return stats


def get_anime_stats(queryset=None):
    if queryset is None:
        queryset = MediaItem.objects.filter(category=MediaItem.Category.ANIME)
    rows = list(_with_progress(queryset))
    watch_time = calculate_watch_time(rows)
    anime_movies = [item for item in rows if item.type == MediaItem.MediaType.MOVIE]
    anime_series = [item for item in rows if item.type == MediaItem.MediaType.SERIES]
    return {
        "items": rows,
        "anime_count": len(rows),
        "anime_movies_count": len(anime_movies),
        "anime_series_count": len(anime_series),
        "completion_rate": calculate_completion_rate(rows),
        "watch_time_minutes": watch_time["minutes"],
        "watch_time_hours": watch_time["hours"],
    }


def get_animation_stats(queryset=None):
    if queryset is None:
        queryset = MediaItem.objects.filter(category=MediaItem.Category.ANIMATION)
    rows = list(_with_progress(queryset))
    watch_time = calculate_watch_time(rows)
    animation_movies = [item for item in rows if item.type == MediaItem.MediaType.MOVIE]
    animation_series = [item for item in rows if item.type == MediaItem.MediaType.SERIES]
    return {
        "items": rows,
        "animation_count": len(rows),
        "animation_movies_count": len(animation_movies),
        "animation_series_count": len(animation_series),
        "completion_rate": calculate_completion_rate(rows),
        "watch_time_minutes": watch_time["minutes"],
        "watch_time_hours": watch_time["hours"],
    }
