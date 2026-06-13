from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.events.models import EventType
from apps.events.services import EventService
from apps.notifications.services.notification_service import NotificationService

from .models import Scholarship


@receiver(post_save, sender=Scholarship)
def scholarship_events(sender, instance, created, **kwargs):
    if created:
        NotificationService.create(instance.user, f"Scholarship tracked: {instance.name}")
    if instance.status == Scholarship.STATUS_APPLIED:
        EventService.record_event(
            instance.user,
            EventType.SCHOLARSHIP_APPLIED,
            "Scholarship",
            instance.id,
            {"name": instance.name, "country": instance.country},
        )
