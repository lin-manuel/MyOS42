from django.core.cache import cache

from analytics.dashboard import dashboard_metrics
from analytics.events import event_metrics
from apps.notifications.services.notification_service import NotificationService


class DashboardService:
    @staticmethod
    def get_dashboard_payload(user):
        cache_key = f"analytics:dashboard-full:user:{user.pk}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        payload = dashboard_metrics(user)
        payload["events"] = event_metrics(user)
        payload["unread_notifications"] = NotificationService.unread_count(user)
        cache.set(cache_key, payload, timeout=300)
        return payload
