from rest_framework import serializers

from .models import AutomationRule, Event


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ("id", "user", "event_type", "entity_type", "entity_id", "metadata", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at")


class AutomationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationRule
        fields = ("id", "user", "trigger_event", "condition", "action", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "user", "created_at", "updated_at")
