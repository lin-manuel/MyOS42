from django.conf import settings
from django.db import models

from apps.common.fields import EncryptedTextField
from apps.common.models import TimeStampedModel


class DiaryEntry(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="diary_entries")
    title = models.CharField(max_length=180, blank=True, default="")
    date = models.DateField()
    content = EncryptedTextField()
    mood = models.CharField(max_length=64, blank=True, default="")
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "date", "created_at"], name="unique_diary_snapshot"),
        ]

    def __str__(self):
        return f"Diary<{self.user_id}> {self.date}"
