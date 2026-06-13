from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.events.models import EventType
from apps.events.services import EventService
from apps.notifications.models import Notification
from .models import Project, Task
from .services.project_service import ProjectService


@receiver(post_save, sender=Project)
def notify_project_updates(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(user=instance.user, message=f"Project '{instance.title}' created.")
        EventService.record_event(instance.user, EventType.PROJECT_CREATED, "Project", instance.id, {"title": instance.title})
    elif instance.status == Project.STATUS_COMPLETED:
        Notification.objects.create(user=instance.user, message=f"Project '{instance.title}' marked completed.")


@receiver(post_save, sender=Task)
def sync_project_on_task_change(sender, instance, created, **kwargs):
    ProjectService.sync_progress(instance.project)
    if instance.status == Task.STATUS_COMPLETED:
        Notification.objects.create(user=instance.project.user, message=f"Task completed: {instance.title}")
        EventService.record_event(
            instance.project.user,
            EventType.TASK_COMPLETED,
            "Task",
            instance.id,
            {"project_id": instance.project_id, "title": instance.title},
        )
