from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "method", "path", "ip_address")
    search_fields = ("path", "ip_address", "user__email")
    readonly_fields = ("created_at",)
