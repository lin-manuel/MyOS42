from django.core.cache import cache

from .models import AutomationRule, Event


class EventService:
    @staticmethod
    def record_event(user, event_type, entity_type, entity_id, metadata=None):
        event = Event.objects.create(
            user=user,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
        )
        cache.clear()
        EventService.evaluate_rules(event)
        return event

    @staticmethod
    def evaluate_rules(event):
        return list(
            AutomationRule.objects.filter(user=event.user, trigger_event=event.event_type, is_active=True).values(
                "id", "condition", "action"
            )
        )
