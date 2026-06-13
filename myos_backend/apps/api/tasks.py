try:
    from celery import shared_task
except ImportError:  # pragma: no cover - optional in minimal environments
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

from django.contrib.auth import get_user_model
from django.core.cache import cache

from analytics.dashboard import dashboard_metrics
from analytics.events import event_metrics
from apps.notifications.services.notification_service import NotificationService


def _warm_user_dashboard(user):
    payload = dashboard_metrics(user)
    payload["events"] = event_metrics(user)
    payload["unread_notifications"] = NotificationService.unread_count(user)
    cache.set(f"analytics:dashboard-full:user:{user.pk}", payload, timeout=300)
    return payload


@shared_task(name="myos.warm_dashboard_cache_for_user")
def warm_dashboard_cache_for_user(user_id):
    user = get_user_model().objects.get(pk=user_id)
    return _warm_user_dashboard(user)


@shared_task(name="myos.warm_all_dashboard_caches")
def warm_all_dashboard_caches():
    payload = []
    for user in get_user_model().objects.iterator():
        payload.append(_warm_user_dashboard(user))
    return payload
