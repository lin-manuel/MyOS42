from django.db.models import Count, Q
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from django.utils import timezone

from apps.events.models import EventType
from apps.events.services import EventService
from apps.notifications.models import Notification
from apps.users.models import CustomUser

from .models import BucketCategory, BucketItem


DEFAULT_BUCKET_CATEGORIES = (
    ("Travel", "fa-plane", "blue"),
    ("Achievements", "fa-trophy", "yellow"),
    ("Experiences", "fa-compass", "orange"),
    ("Learning", "fa-book", "green"),
    ("Wealth", "fa-coins", "brown"),
)


def sync_bucket_category_counts(category_id):
    counts = BucketItem.objects.filter(category_id=category_id).aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=BucketItem.STATUS_COMPLETED)),
    )
    BucketCategory.objects.filter(id=category_id).update(
        item_count=counts["total"] or 0,
        completed_count=counts["completed"] or 0,
    )


@receiver(post_save, sender=CustomUser)
def ensure_default_bucket_categories(sender, instance, created, **kwargs):
    if not created:
        return
    for name, icon, color in DEFAULT_BUCKET_CATEGORIES:
        BucketCategory.objects.get_or_create(
            user=instance,
            name=name,
            defaults={"icon": icon, "color": color},
        )


@receiver(post_save, sender=BucketItem)
def notify_bucket_progress(sender, instance, created, **kwargs):
    sync_bucket_category_counts(instance.category_id)
    if created:
        Notification.objects.create(user=instance.user, message=f"Bucket item created: {instance.title}")
        return

    if instance.status == BucketItem.STATUS_COMPLETED and instance.completed_at is None:
        instance.completed_at = timezone.now()
        instance.save(update_fields=["completed_at", "updated_at"])
        return

    if instance.completed_at is not None and instance.status != BucketItem.STATUS_COMPLETED:
        instance.completed_at = None
        instance.save(update_fields=["completed_at", "updated_at"])
        return

    if instance.status == BucketItem.STATUS_COMPLETED:
        Notification.objects.create(user=instance.user, message=f"Bucket item completed: {instance.title}")
        EventService.record_event(
            instance.user,
            EventType.BUCKET_ITEM_COMPLETED,
            "BucketItem",
            instance.id,
            {"title": instance.title},
        )


@receiver(post_delete, sender=BucketItem)
def sync_bucket_counts_on_delete(sender, instance, **kwargs):
    sync_bucket_category_counts(instance.category_id)
