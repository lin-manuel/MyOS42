from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class EventType:
    USER_LOGIN = "USER_LOGIN"
    PROJECT_CREATED = "PROJECT_CREATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TRANSACTION_ADDED = "TRANSACTION_ADDED"
    MEDIA_WATCHED = "MEDIA_WATCHED"
    DIARY_ENTRY_CREATED = "DIARY_ENTRY_CREATED"
    BUCKET_ITEM_COMPLETED = "BUCKET_ITEM_COMPLETED"
    SCHOLARSHIP_APPLIED = "SCHOLARSHIP_APPLIED"


EVENT_TYPES = [
    (EventType.USER_LOGIN, "User Login"),
    (EventType.PROJECT_CREATED, "Project Created"),
    (EventType.TASK_COMPLETED, "Task Completed"),
    (EventType.TRANSACTION_ADDED, "Transaction Added"),
    (EventType.MEDIA_WATCHED, "Media Watched"),
    (EventType.DIARY_ENTRY_CREATED, "Diary Entry Created"),
    (EventType.BUCKET_ITEM_COMPLETED, "Bucket Item Completed"),
    (EventType.SCHOLARSHIP_APPLIED, "Scholarship Applied"),
]


class Event(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=100, choices=EVENT_TYPES, db_index=True)
    entity_type = models.CharField(max_length=100)
    entity_id = models.PositiveIntegerField()
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "event_type", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"{self.event_type}#{self.entity_type}:{self.entity_id}"


class AutomationRule(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="automation_rules")
    trigger_event = models.CharField(max_length=100, choices=EVENT_TYPES)
    condition = models.TextField(blank=True, default="")
    action = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["trigger_event", "-created_at"]

    def __str__(self):
        return f"{self.user_id}:{self.trigger_event}"
