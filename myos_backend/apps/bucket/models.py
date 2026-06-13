from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class BucketCategory(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bucket_categories")
    name = models.CharField(max_length=120)
    icon = models.CharField(max_length=64, blank=True, default="")
    color = models.CharField(max_length=20, blank=True, default="")
    item_count = models.PositiveIntegerField(default=0)
    completed_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class BucketItem(TimeStampedModel):
    STATUS_IDEA = "idea"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = (
        (STATUS_IDEA, "Idea"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bucket_items")
    category = models.ForeignKey(BucketCategory, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    starred = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    target_date = models.DateField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["status", "target_date", "created_at"]

    def __str__(self):
        return self.title
