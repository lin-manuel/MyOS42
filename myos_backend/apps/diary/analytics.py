from collections import Counter
from datetime import timedelta

from django.utils import timezone

from .models import DiaryEntry


def mood_trends(user):
    counter = Counter(entry.mood for entry in DiaryEntry.objects.filter(user=user) if entry.mood)
    return [{"mood": mood, "count": count} for mood, count in counter.most_common()]


def writing_streak(user):
    dates = list(DiaryEntry.objects.filter(user=user).values_list("date", flat=True).distinct().order_by("-date"))
    if not dates:
        return 0
    streak = 0
    expected = timezone.localdate()
    for entry_date in dates:
        if entry_date == expected:
            streak += 1
            expected = entry_date - timedelta(days=1)
        elif streak == 0:
            expected = entry_date - timedelta(days=1)
            streak += 1
        else:
            break
    return streak
