from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.events.models import EventType
from apps.events.services import EventService
from apps.notifications.models import Notification
from .models import FinanceEntry


@receiver(post_save, sender=FinanceEntry)
def notify_high_expense(sender, instance, created, **kwargs):
    if created:
        EventService.record_event(
            instance.user,
            EventType.TRANSACTION_ADDED,
            "FinanceEntry",
            instance.id,
            {"type": instance.type, "amount": float(instance.amount), "date": instance.date.isoformat()},
        )
        if instance.type == FinanceEntry.TYPE_EXPENSE and instance.amount >= Decimal("1000"):
            Notification.objects.create(
                user=instance.user,
                message=f"High expense recorded: {instance.amount} on {instance.date}",
            )
