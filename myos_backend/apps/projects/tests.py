from django.test import TestCase

from apps.projects.analytics import task_completion_rate
from apps.projects.models import Project, Task
from apps.users.models import CustomUser


class ProjectAnalyticsTests(TestCase):
    def test_completion_rate(self):
        user = CustomUser.objects.create_user(
            email="projects@example.com",
            password="test-password-123",
            first_name="Project",
            last_name="User",
        )
        project = Project.objects.create(user=user, title="MyOS", status=Project.STATUS_IN_PROGRESS)
        Task.objects.create(project=project, title="Plan", status=Task.STATUS_COMPLETED)
        Task.objects.create(project=project, title="Build", status=Task.STATUS_TODO)
        payload = task_completion_rate(user)
        self.assertEqual(payload["completed"], 1)
        self.assertEqual(payload["total"], 2)
