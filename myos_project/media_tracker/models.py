from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class MediaItem(models.Model):
    class Category(models.TextChoices):
        MOVIE = "MOVIE", "Movies"
        SERIES = "SERIES", "Series"
        ANIME = "ANIME", "Anime"
        ANIMATION = "ANIMATION", "Animation"

    class MediaType(models.TextChoices):
        MOVIE = "MOVIE", "Movie"
        SERIES = "SERIES", "Series"

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        WATCHING = "WATCHING", "Watching"
        COMPLETED = "COMPLETED", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tracked_media",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=220)
    category = models.CharField(max_length=20, choices=Category.choices)
    type = models.CharField(max_length=20, choices=MediaType.choices)
    genre = models.CharField(max_length=160, blank=True, default="")
    studio = models.CharField(max_length=160, blank=True, default="")
    country = models.CharField(max_length=120, blank=True, default="")
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1888), MaxValueValidator(2200)],
    )
    platform = models.CharField(max_length=120, blank=True, default="")
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Movie duration in minutes.",
    )
    total_seasons = models.PositiveIntegerField(default=1)
    total_episodes = models.PositiveIntegerField(default=1)
    episode_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Episode duration in minutes.",
    )
    date_added = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)

    class Meta:
        ordering = ["-date_added", "-id"]
        indexes = [
            models.Index(fields=["category", "type", "status"]),
            models.Index(fields=["platform"]),
            models.Index(fields=["year"]),
        ]

    def __str__(self):
        return self.title

    def latest_progress_entry(self):
        prefetched = getattr(self, "_prefetched_objects_cache", {})
        if "progress_entries" in prefetched:
            entries = prefetched["progress_entries"]
            return entries[0] if entries else None
        return self.progress_entries.order_by("-date_watched", "-id").first()

    def progress_percent(self):
        latest = self.latest_progress_entry()
        if self.type == self.MediaType.MOVIE:
            completed = self.status == self.Status.COMPLETED or bool(latest and latest.completed)
            return 100 if completed else 0
        total = max(self.total_episodes or 0, 0)
        if total <= 0:
            return 0
        watched = latest.episodes_watched if latest else 0
        return int(min(100, max(0, (watched / total) * 100)))


class MediaProgress(models.Model):
    media_item = models.ForeignKey(
        MediaItem,
        on_delete=models.CASCADE,
        related_name="progress_entries",
    )
    episodes_watched = models.PositiveIntegerField(default=0)
    current_season = models.PositiveIntegerField(default=1)
    current_episode = models.PositiveIntegerField(default=0)
    date_watched = models.DateField(default=timezone.now, db_index=True)
    completed = models.BooleanField(default=False)
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Rating from 1 to 10.",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-date_watched", "-id"]
        indexes = [
            models.Index(fields=["date_watched"]),
            models.Index(fields=["completed"]),
        ]

    def __str__(self):
        return f"{self.media_item.title} ({self.date_watched})"

    def save(self, *args, **kwargs):
        media = self.media_item
        if media.type == MediaItem.MediaType.MOVIE:
            self.current_season = 1
            self.current_episode = 1 if self.completed else max(self.current_episode, 0)
            self.episodes_watched = 1 if self.completed else min(self.episodes_watched, 1)
        else:
            total = max(media.total_episodes or 0, 0)
            if total > 0:
                self.episodes_watched = min(self.episodes_watched, total)
                if self.episodes_watched >= total:
                    self.completed = True
        super().save(*args, **kwargs)

    @property
    def watch_time_minutes(self):
        media = self.media_item
        if media.type == MediaItem.MediaType.MOVIE:
            return media.duration or 0
        return (self.episodes_watched or 0) * (media.episode_duration or 0)

