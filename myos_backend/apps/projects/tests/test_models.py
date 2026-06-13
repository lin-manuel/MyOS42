from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.projects.models import Project, ProjectAttachment
from apps.users.models import CustomUser


class ProjectAttachmentTests(TestCase):
    def test_attachment_can_be_created_for_project(self):
        user = CustomUser.objects.create_user(
            email="attachment@example.com",
            password="test-password-123",
            first_name="Attach",
            last_name="User",
        )
        project = Project.objects.create(user=user, title="Attachment Test")
        attachment = ProjectAttachment.objects.create(
            user=user,
            project=project,
            title="Scope",
            file=SimpleUploadedFile("scope.txt", b"hello world", content_type="text/plain"),
        )
        self.assertEqual(attachment.project, project)
        self.assertEqual(attachment.user, user)
