from collections import Counter

from django.db.models import Count
from django.db.models.functions import TruncMonth

from .models import MediaItem, MediaProgress
from .services.media_service import MediaService


def watch_time(user):
    items = list(MediaService.with_progress(user))
    return MediaService.calculate_watch_time(items)


def completion_rate(user):
    items = list(MediaService.with_progress(user))
    return MediaService.calculate_completion_rate(items)


def genre_distribution(user):
    counter = Counter()
    for item in MediaItem.objects.filter(user=user):
        for genre in [chunk.strip() for chunk in (item.genre or "").split(",") if chunk.strip()]:
            counter[genre] += 1
    return [{"genre": genre, "count": count} for genre, count in counter.most_common()]


def movies_per_month(user):
    rows = (
        MediaItem.objects.filter(user=user, type=MediaItem.TYPE_MOVIE)
        .annotate(month=TruncMonth("date_added"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    return [{"month": row["month"].strftime("%Y-%m") if row["month"] else "", "count": row["total"]} for row in rows]


def watch_history(user):
    return list(
        MediaProgress.objects.filter(media_item__user=user)
        .values("media_item__title", "episodes_watched", "completed", "watched_at")
        .order_by("-watched_at")[:50]
    )
