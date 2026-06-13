from django.contrib import admin

from .models import Episode, MediaItem, MediaProgress, Season


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "type", "status", "platform", "studio", "year", "date_added")
    list_filter = ("category", "type", "status", "platform")
    search_fields = ("title", "description", "genre", "studio", "user__email")


@admin.register(MediaProgress)
class MediaProgressAdmin(admin.ModelAdmin):
    list_display = ("media_item", "episodes_watched", "current_season", "current_episode", "completed", "watched_at")
    list_filter = ("completed", "watched_at")
    search_fields = ("media_item__title", "media_item__user__email", "notes")


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("media_item", "number", "title")
    search_fields = ("media_item__title", "title")


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ("season", "number", "title", "duration", "air_date")
    search_fields = ("season__media_item__title", "title")
