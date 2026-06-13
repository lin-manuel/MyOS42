from django.contrib import admin

from .models import AutomationRule, Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "entity_type", "entity_id", "user", "created_at")
    list_filter = ("event_type", "entity_type", "created_at")
    search_fields = ("user__email", "entity_type")


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = ("user", "trigger_event", "is_active", "created_at")
    list_filter = ("trigger_event", "is_active")
    search_fields = ("user__email", "action", "condition")
