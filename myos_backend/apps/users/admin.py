from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, UserOTP, UserProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "email",
        "first_name",
        "last_name",
        "avatar_initials",
        "country",
        "currency",
        "is_staff",
        "is_active",
        "is_email_verified",
    )
    ordering = ("email",)
    search_fields = ("email", "first_name", "last_name", "country")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "avatar", "timezone", "currency", "country", "preferences")}),
        ("Security", {"fields": ("is_email_verified", "two_factor_enabled")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at", "last_login")
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )


@admin.register(UserOTP)
class UserOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "code", "expires_at", "is_used", "created_at")
    search_fields = ("user__email", "purpose", "code")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "timezone", "currency", "country")
    search_fields = ("user__email", "full_name", "country")
