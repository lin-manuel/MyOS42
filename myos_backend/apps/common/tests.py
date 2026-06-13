from django.test import TestCase

from apps.common.services import FileSecurityService


class FileSecurityServiceTests(TestCase):
    def test_scan_stub(self):
        result = FileSecurityService.scan(None)
        self.assertEqual(result["status"], "clean")
