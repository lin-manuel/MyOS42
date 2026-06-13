from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    profile_photo = models.ImageField(upload_to="profile_photos/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    def __str__(self):
        return self.email


class TrustedDevice(models.Model):
    """Stores fingerprints of devices the user has verified."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trusted_devices")
    device_fingerprint = models.CharField(max_length=255)
    device_name = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    trusted_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "device_fingerprint")

    def __str__(self):
        return f"{self.user.email} — {self.device_name or 'Device'}"


class LoginActivity(models.Model):
    """Logs every login attempt for security audit."""

    STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
        ("blocked", "Blocked"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="login_activity",
        null=True,
        blank=True,
    )
    email_attempted = models.EmailField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_fingerprint = models.CharField(max_length=255, blank=True)
    user_agent = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    failure_reason = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.email_attempted} — {self.status} — {self.timestamp}"
