from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.events.models import EventType
from apps.events.services import EventService
from apps.notifications.models import Notification
from .models import CustomUser, UserProfile


@receiver(post_save, sender=CustomUser)
def create_welcome_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(user=instance, message="Welcome to MyOS. Your secure dashboard is ready.")
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                "full_name": f"{instance.first_name} {instance.last_name}".strip(),
                "timezone": instance.timezone,
                "currency": instance.currency,
                "country": instance.country,
            },
        )
        EventService.record_event(instance, EventType.USER_LOGIN, "User", instance.id, {"source": "signup"})
