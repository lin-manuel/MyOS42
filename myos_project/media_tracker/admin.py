from django.contrib import admin

from .models import MediaItem, MediaProgress


class MediaProgressInline(admin.TabularInline):
    model = MediaProgress
    extra = 0
    fields = (
        "date_watched",
        "episodes_watched",
        "current_season",
        "current_episode",
        "completed",
        "rating",
    )


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "type",
        "status",
        "platform",
        "year",
        "date_added",
    )
    list_filter = ("category", "status", "platform", "year", "type")
    search_fields = ("title", "genre", "studio")
    ordering = ("-date_added", "-id")
    inlines = [MediaProgressInline]


@admin.register(MediaProgress)
class MediaProgressAdmin(admin.ModelAdmin):
    list_display = (
        "media_item",
        "date_watched",
        "episodes_watched",
        "current_season",
        "current_episode",
        "completed",
        "rating",
    )
    list_filter = (
        "completed",
        "date_watched",
        "media_item__category",
        "media_item__status",
        "media_item__platform",
        "media_item__year",
    )
    search_fields = ("media_item__title", "media_item__genre", "media_item__studio", "notes")
    autocomplete_fields = ("media_item",)
    ordering = ("-date_watched", "-id")
