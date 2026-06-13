from apps.notifications.models import Notification


class NotificationService:
    @staticmethod
    def create(user, message, category="", link=""):
        return Notification.objects.create(user=user, message=message, category=category, link=link)

    @staticmethod
    def unread_count(user):
        return Notification.objects.filter(user=user, read=False).count()
