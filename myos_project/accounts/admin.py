from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import LoginActivity, TrustedDevice, User


@admin.register(User)
class UserAdminConfig(UserAdmin):
    model = User
    list_display = ("email", "username", "is_email_verified", "is_active", "is_staff")
    list_filter = ("is_email_verified", "is_active", "is_staff")
    ordering = ("email",)
    search_fields = ("email", "username", "first_name", "last_name")
    fieldsets = UserAdmin.fieldsets + (
        ("MyOS Profile", {"fields": ("is_email_verified", "profile_photo")}),
    )


@admin.register(TrustedDevice)
class TrustedDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "device_name", "ip_address", "trusted_at", "last_seen")
    search_fields = ("user__email", "device_name", "device_fingerprint")


@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ("email_attempted", "status", "timestamp", "ip_address")
    list_filter = ("status",)
    search_fields = ("email_attempted", "ip_address", "device_fingerprint")
