from collections import Counter, defaultdict
from datetime import timedelta
import hashlib

from django.core.cache import cache
from django.db.models import Count, Max, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from .models import MediaItem, MediaProgress
from .services import calculate_completion_rate, calculate_watch_time


CACHE_TIMEOUT_SECONDS = 300


def _analytics_cache_key(prefix):
    last_item_added = MediaItem.objects.aggregate(last=Max("date_added")).get("last")
    last_progress_id = MediaProgress.objects.aggregate(last=Max("id")).get("last")
    item_count = MediaItem.objects.count()
    progress_count = MediaProgress.objects.count()
    signature = "|".join(
        [
            str(prefix),
            str(item_count),
            str(progress_count),
            last_item_added.isoformat() if last_item_added else "",
            str(last_progress_id or ""),
        ]
    )
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()
    return f"media_tracker:{prefix}:{digest}"


def _build_genre_distribution(items):
    counter = Counter()
    for item in items:
        raw = (item.genre or "").strip()
        if not raw:
            continue
        genres = [chunk.strip() for chunk in raw.split(",") if chunk.strip()]
        if not genres:
            genres = [raw]
        for genre in genres:
            counter[genre] += 1
    return [{"genre": key, "count": value} for key, value in counter.most_common()]


def _month_series(queryset, field_name, value_name=None):
    rows = (
        queryset.annotate(month=TruncMonth(field_name))
        .values("month")
        .annotate(total=Sum(value_name) if value_name else Count("id"))
        .order_by("month")
    )
    return [
        {
            "month": row["month"].strftime("%Y-%m") if row["month"] else "",
            "value": int(row["total"] or 0),
        }
        for row in rows
    ]


def movies_analytics():
    cache_key = _analytics_cache_key("movies")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    items = list(MediaItem.objects.filter(category=MediaItem.Category.MOVIE))
    watched = len([item for item in items if item.status == MediaItem.Status.COMPLETED])
    total = len(items)
    completion_rate = round((watched / total) * 100, 2) if total else 0.0

    per_month_rows = (
        MediaItem.objects.filter(category=MediaItem.Category.MOVIE)
        .annotate(month=TruncMonth("date_added"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    movies_per_month = [
        {"month": row["month"].strftime("%Y-%m") if row["month"] else "", "count": int(row["total"] or 0)}
        for row in per_month_rows
    ]

    result = {
        "movies_watched_count": watched,
        "movies_remaining_count": max(0, total - watched),
        "movies_per_month": movies_per_month,
        "genre_distribution": _build_genre_distribution(items),
        "completion_rate": completion_rate,
        "watch_time": calculate_watch_time(items),
    }
    cache.set(cache_key, result, CACHE_TIMEOUT_SECONDS)
    return result


def series_analytics():
    cache_key = _analytics_cache_key("series")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    items = list(MediaItem.objects.filter(category=MediaItem.Category.SERIES))
    completed = len([item for item in items if item.status == MediaItem.Status.COMPLETED])
    in_progress = len([item for item in items if item.status == MediaItem.Status.WATCHING])

    progress_qs = MediaProgress.objects.filter(media_item__category=MediaItem.Category.SERIES)
    episodes_watched_per_month = _month_series(progress_qs, "date_watched", "episodes_watched")

    cutoff = timezone.now().date() - timedelta(days=56)
    weekly_rows = defaultdict(int)
    for row in progress_qs.filter(date_watched__gte=cutoff):
        week = row.date_watched - timedelta(days=row.date_watched.weekday())
        weekly_rows[week] += row.episodes_watched
    weekly_values = list(weekly_rows.values())
    average_per_week = round(sum(weekly_values) / len(weekly_values), 2) if weekly_values else 0.0

    result = {
        "series_completed": completed,
        "series_in_progress": in_progress,
        "episodes_watched_per_month": episodes_watched_per_month,
        "average_episodes_per_week": average_per_week,
        "watch_time": calculate_watch_time(items),
        "completion_rate": calculate_completion_rate(items),
        "genre_distribution": _build_genre_distribution(items),
    }
    cache.set(cache_key, result, CACHE_TIMEOUT_SECONDS)
    return result


def anime_analytics():
    cache_key = _analytics_cache_key("anime")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    items = list(MediaItem.objects.filter(category=MediaItem.Category.ANIME))
    episodes_watched = (
        MediaProgress.objects.filter(media_item__category=MediaItem.Category.ANIME).aggregate(total=Sum("episodes_watched"))["total"]
        or 0
    )
    result = {
        "anime_completion_rate": calculate_completion_rate(items),
        "anime_by_genre": _build_genre_distribution(items),
        "episodes_watched": int(episodes_watched),
        "watch_time": calculate_watch_time(items),
    }
    cache.set(cache_key, result, CACHE_TIMEOUT_SECONDS)
    return result


def global_media_analytics():
    cache_key = _analytics_cache_key("global")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    items = list(MediaItem.objects.all().prefetch_related("progress_entries"))
    movies = [item for item in items if item.category == MediaItem.Category.MOVIE]
    series = [item for item in items if item.category == MediaItem.Category.SERIES]
    anime = [item for item in items if item.category == MediaItem.Category.ANIME]

    anime_episodes_watched = (
        MediaProgress.objects.filter(media_item__category=MediaItem.Category.ANIME).aggregate(total=Sum("episodes_watched"))["total"]
        or 0
    )
    watch_time = calculate_watch_time(items)

    result = {
        "movies_watched": len([item for item in movies if item.status == MediaItem.Status.COMPLETED]),
        "movies_total": len(movies),
        "series_completed": len([item for item in series if item.status == MediaItem.Status.COMPLETED]),
        "series_total": len(series),
        "anime_episodes_watched": int(anime_episodes_watched),
        "total_watch_time": watch_time,
    }
    cache.set(cache_key, result, CACHE_TIMEOUT_SECONDS)
    return result
