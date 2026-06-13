from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class MediaItem(TimeStampedModel):
    CATEGORY_MOVIE = "movie"
    CATEGORY_SERIES = "series"
    CATEGORY_ANIME = "anime"
    CATEGORY_ANIMATION = "animation"

    CATEGORY_CHOICES = (
        (CATEGORY_MOVIE, "Movies"),
        (CATEGORY_SERIES, "Series"),
        (CATEGORY_ANIME, "Anime"),
        (CATEGORY_ANIMATION, "Animation"),
    )

    TYPE_MOVIE = "movie"
    TYPE_SERIES = "series"

    TYPE_CHOICES = (
        (TYPE_MOVIE, "Movie"),
        (TYPE_SERIES, "Series"),
    )

    STATUS_PLANNED = "planned"
    STATUS_WATCHING = "watching"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = (
        (STATUS_PLANNED, "Planned"),
        (STATUS_WATCHING, "Watching"),
        (STATUS_COMPLETED, "Completed"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="media_items")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True, default="")
    studio = models.CharField(max_length=120, blank=True, default="")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    genre = models.CharField(max_length=180, blank=True, default="")
    country = models.CharField(max_length=120, blank=True, default="")
    platform = models.CharField(max_length=120, blank=True, default="")
    cover_image = models.ImageField(upload_to="media/covers/", blank=True, null=True)
    source_file = models.FileField(upload_to="media/files/", blank=True, null=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True, help_text="Movie duration in minutes.")
    total_seasons = models.PositiveIntegerField(default=1)
    total_episodes = models.PositiveIntegerField(default=1)
    episode_duration = models.PositiveIntegerField(null=True, blank=True, help_text="Episode duration in minutes.")
    date_added = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)

    class Meta:
        ordering = ["-date_added", "-created_at"]
        indexes = [
            models.Index(fields=["user", "category", "type", "status"]),
            models.Index(fields=["user", "year"]),
        ]

    def __str__(self):
        return self.title


class Season(TimeStampedModel):
    media_item = models.ForeignKey(MediaItem, on_delete=models.CASCADE, related_name="seasons")
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=160, blank=True, default="")

    class Meta:
        ordering = ["number"]
        unique_together = ("media_item", "number")

    def __str__(self):
        return f"{self.media_item.title} S{self.number}"


class Episode(TimeStampedModel):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="episodes")
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=160, blank=True, default="")
    duration = models.PositiveIntegerField(null=True, blank=True)
    air_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["number"]
        unique_together = ("season", "number")

    def __str__(self):
        return f"{self.season}E{self.number}"


class MediaProgress(TimeStampedModel):
    media_item = models.ForeignKey(MediaItem, on_delete=models.CASCADE, related_name="progress_entries")
    episodes_watched = models.PositiveIntegerField(default=0)
    current_season = models.PositiveIntegerField(default=1)
    current_episode = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    notes = models.TextField(blank=True, default="")
    watched_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-watched_at", "-created_at"]

    @property
    def watch_time_minutes(self):
        if self.media_item.type == MediaItem.TYPE_MOVIE:
            return self.media_item.duration or 0
        return (self.episodes_watched or 0) * (self.media_item.episode_duration or 0)

    def __str__(self):
        return f"{self.media_item.title}:{self.episodes_watched}"
