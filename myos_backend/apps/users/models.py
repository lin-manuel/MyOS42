from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    timezone = models.CharField(max_length=64, default="UTC")
    currency = models.CharField(max_length=16, default="USD")
    country = models.CharField(max_length=80, blank=True, default="")
    preferences = models.JSONField(default=dict, blank=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_email_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    @property
    def avatar_initials(self):
        initials = "".join(part[:1].upper() for part in [self.first_name, self.last_name] if part)
        if initials:
            return initials[:3]
        return (self.email[:2] if self.email else "U").upper()

    @property
    def display_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def __str__(self):
        return self.email


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=180, blank=True, default="")
    avatar = models.ImageField(upload_to="profiles/", blank=True, null=True)
    timezone = models.CharField(max_length=64, default="UTC")
    currency = models.CharField(max_length=16, default="USD")
    country = models.CharField(max_length=80, blank=True, default="")

    def __str__(self):
        return self.full_name or self.user.email


class UserOTP(TimeStampedModel):
    PURPOSE_CHOICES = (
        ("signup", "Signup Verification"),
        ("login_2fa", "Login 2FA"),
        ("password_reset", "Password Reset"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    @classmethod
    def default_expiry(cls):
        return timezone.now() + timedelta(minutes=10)

    def is_expired(self):
        return timezone.now() > self.expires_at
