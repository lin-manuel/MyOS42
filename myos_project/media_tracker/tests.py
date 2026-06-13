from datetime import date

from django.test import TestCase
from django.urls import reverse

from .models import MediaItem, MediaProgress


class MediaTrackerViewsTests(TestCase):
    def setUp(self):
        self.movie = MediaItem.objects.create(
            title="Interstellar",
            category=MediaItem.Category.MOVIE,
            type=MediaItem.MediaType.MOVIE,
            genre="Sci-Fi",
            duration=169,
            status=MediaItem.Status.PLANNED,
        )
        self.series = MediaItem.objects.create(
            title="Dark",
            category=MediaItem.Category.SERIES,
            type=MediaItem.MediaType.SERIES,
            genre="Sci-Fi, Thriller",
            total_seasons=3,
            total_episodes=26,
            episode_duration=55,
            status=MediaItem.Status.WATCHING,
        )

    def test_dashboard_renders(self):
        response = self.client.get(reverse("media"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Media Dashboard")

    def test_htmx_dashboard_renders_partial_only(self):
        response = self.client.get(reverse("media"), HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="page-media"', html=False)
        self.assertNotContains(response, '<html', html=False)
        self.assertNotContains(response, 'class="sidebar"', html=False)

    def test_add_media_creates_record(self):
        payload = {
            "title": "Arcane",
            "category": MediaItem.Category.ANIMATION,
            "type": MediaItem.MediaType.SERIES,
            "genre": "Fantasy",
            "studio": "Fortiche",
            "country": "France",
            "year": 2021,
            "platform": "Netflix",
            "duration": "",
            "total_seasons": 2,
            "total_episodes": 18,
            "episode_duration": 42,
            "status": MediaItem.Status.PLANNED,
        }
        response = self.client.post(reverse("add_media"), payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MediaItem.objects.filter(title="Arcane").exists())

    def test_htmx_add_media_invalid_returns_partial_with_400(self):
        payload = {
            "category": MediaItem.Category.ANIMATION,
            "type": MediaItem.MediaType.SERIES,
            "status": MediaItem.Status.PLANNED,
        }
        response = self.client.post(reverse("add_media"), payload, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'id="page-media"', html=False, status_code=400)
        self.assertContains(response, "<form", html=False, status_code=400)
        self.assertNotContains(response, 'class="sidebar"', html=False, status_code=400)

    def test_htmx_add_media_success_returns_hx_location(self):
        payload = {
            "title": "Arcane",
            "category": MediaItem.Category.ANIMATION,
            "type": MediaItem.MediaType.SERIES,
            "genre": "Fantasy",
            "studio": "Fortiche",
            "country": "France",
            "year": 2021,
            "platform": "Netflix",
            "duration": "",
            "total_seasons": 2,
            "total_episodes": 18,
            "episode_duration": 42,
            "status": MediaItem.Status.PLANNED,
        }
        response = self.client.post(reverse("add_media"), payload, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("HX-Location"), reverse("animation_view"))
        self.assertTrue(MediaItem.objects.filter(title="Arcane").exists())

    def test_update_progress_marks_item_completed(self):
        payload = {
            "episodes_watched": 26,
            "current_season": 3,
            "current_episode": 8,
            "date_watched": date.today().isoformat(),
            "completed": "on",
            "rating": 9,
            "notes": "Finished",
        }
        response = self.client.post(reverse("update_progress", args=[self.series.id]), payload)
        self.assertEqual(response.status_code, 302)

        self.series.refresh_from_db()
        self.assertEqual(self.series.status, MediaItem.Status.COMPLETED)
        self.assertTrue(MediaProgress.objects.filter(media_item=self.series).exists())

    def test_htmx_update_progress_success_returns_hx_location(self):
        payload = {
            "episodes_watched": 26,
            "current_season": 3,
            "current_episode": 8,
            "date_watched": date.today().isoformat(),
            "completed": "on",
            "rating": 9,
            "notes": "Finished",
        }
        response = self.client.post(
            reverse("update_progress", args=[self.series.id]),
            payload,
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("HX-Location"), reverse("series_view"))

    def test_media_api_endpoints(self):
        MediaProgress.objects.create(
            media_item=self.series,
            episodes_watched=10,
            current_season=2,
            current_episode=1,
            completed=False,
        )

        stats_response = self.client.get(reverse("api_media_stats"))
        self.assertEqual(stats_response.status_code, 200)
        stats_data = stats_response.json()
        for key in ("completion_rate", "genre_distribution", "watch_time", "episodes_per_month"):
            self.assertIn(key, stats_data)

        movies_response = self.client.get(reverse("api_media_movies"))
        self.assertEqual(movies_response.status_code, 200)
        self.assertIn("movies_watched_count", movies_response.json())

        series_response = self.client.get(reverse("api_media_series"))
        self.assertEqual(series_response.status_code, 200)
        self.assertIn("episodes_per_month", series_response.json())

        anime_response = self.client.get(reverse("api_media_anime"))
        self.assertEqual(anime_response.status_code, 200)
        self.assertIn("completion_rate", anime_response.json())
