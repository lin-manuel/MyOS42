from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.events.models import EventType
from apps.events.services import EventService
from apps.notifications.services.notification_service import NotificationService

from .models import MediaItem, MediaProgress
from .services.media_service import MediaService


@receiver(post_save, sender=MediaItem)
def notify_media_created(sender, instance, created, **kwargs):
    if created:
        NotificationService.create(instance.user, f"Media added: {instance.title}", category="media")


@receiver(post_save, sender=MediaProgress)
def notify_media_progress(sender, instance, created, **kwargs):
    MediaService.sync_media_status(instance)
    if created:
        NotificationService.create(
            instance.media_item.user,
            f"Progress updated: {instance.media_item.title}",
            category="media",
        )
        EventService.record_event(
            instance.media_item.user,
            EventType.MEDIA_WATCHED,
            "MediaItem",
            instance.media_item_id,
            {
                "episodes_watched": instance.episodes_watched,
                "current_season": instance.current_season,
                "current_episode": instance.current_episode,
                "completed": instance.completed,
            },
        )
