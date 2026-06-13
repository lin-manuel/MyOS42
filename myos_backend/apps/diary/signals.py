from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.events.models import EventType
from apps.events.services import EventService
from apps.notifications.models import Notification
from .models import DiaryEntry


@receiver(post_save, sender=DiaryEntry)
def notify_diary_entry_saved(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(user=instance.user, message=f"Diary entry saved for {instance.date}.")
        EventService.record_event(
            instance.user,
            EventType.DIARY_ENTRY_CREATED,
            "DiaryEntry",
            instance.id,
            {"date": instance.date.isoformat(), "mood": instance.mood},
        )
