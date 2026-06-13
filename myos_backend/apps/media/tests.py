from django.test import TestCase

from apps.media.analytics import completion_rate, watch_time
from apps.media.models import MediaItem, MediaProgress
from apps.users.models import CustomUser


class MediaAnalyticsTests(TestCase):
    def test_watch_time(self):
        user = CustomUser.objects.create_user(
            email="media@example.com",
            password="test-password-123",
            first_name="Media",
            last_name="User",
        )
        item = MediaItem.objects.create(
            user=user,
            title="Dark",
            category=MediaItem.CATEGORY_SERIES,
            type=MediaItem.TYPE_SERIES,
            total_episodes=10,
            episode_duration=50,
        )
        MediaProgress.objects.create(media_item=item, episodes_watched=4, current_season=1, current_episode=4)
        self.assertEqual(watch_time(user)["minutes"], 200)
        self.assertEqual(completion_rate(user), 0.0)
