from django.utils import timezone

from apps.projects.models import Project, ProjectNote, Task


class ProjectService:
    @staticmethod
    def sync_progress(project: Project):
        total = project.tasks.count()
        completed = project.tasks.filter(status=Task.STATUS_COMPLETED).count()
        project.progress = int((completed / total) * 100) if total else project.progress
        if project.progress >= 100:
            project.status = Project.STATUS_COMPLETED
        elif project.progress > 0 and project.status in {Project.STATUS_IDEA, Project.STATUS_PENDING}:
            project.status = Project.STATUS_IN_PROGRESS
        project.save(update_fields=["progress", "status", "updated_at"])
        return project

    @staticmethod
    def update_progress(project: Project, progress: int):
        project.progress = max(0, min(100, progress))
        if project.progress >= 100:
            project.status = Project.STATUS_COMPLETED
        elif project.progress > 0 and project.status in {Project.STATUS_IDEA, Project.STATUS_PENDING}:
            project.status = Project.STATUS_IN_PROGRESS
        project.save(update_fields=["progress", "status", "updated_at"])
        return project

    @staticmethod
    def complete_task(task: Task):
        task.status = Task.STATUS_COMPLETED
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at", "updated_at"])
        ProjectService.sync_progress(task.project)
        return task

    @staticmethod
    def create_note(project: Project, content: str):
        return ProjectNote.objects.create(project=project, content=content)
