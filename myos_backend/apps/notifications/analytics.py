from .services.notification_service import NotificationService


def unread_summary(user):
    return {"unread": NotificationService.unread_count(user)}
