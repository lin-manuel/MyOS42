from django.test import TestCase

from apps.events.models import EventType
from apps.events.services import EventService
from apps.users.models import CustomUser


class EventServiceTests(TestCase):
    def test_records_event(self):
        user = CustomUser.objects.create_user(
            email="events@example.com",
            password="test-password-123",
            first_name="Events",
            last_name="User",
        )
        event = EventService.record_event(user, EventType.USER_LOGIN, "User", user.id, {"source": "test"})
        self.assertEqual(event.event_type, EventType.USER_LOGIN)
        self.assertEqual(event.metadata["source"], "test")
