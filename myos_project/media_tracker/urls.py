from django.urls import path

from . import views

urlpatterns = [
    path("media/", views.media_dashboard, name="media"),
    path("media/dashboard/", views.media_dashboard, name="media_dashboard"),
    path("media/movies/", views.movies_view, name="movies_view"),
    path("media/series/", views.series_view, name="series_view"),
    path("media/anime/", views.anime_view, name="anime_view"),
    path("media/animation/", views.animation_view, name="animation_view"),
    path("media/add/", views.add_media, name="add_media"),
    path("media/edit/<int:item_id>/", views.edit_media, name="edit_media"),
    path("media/delete/<int:item_id>/", views.delete_media, name="delete_media"),
    path("media/progress/<int:item_id>/", views.update_progress, name="update_progress"),
    path("api/media/stats/", views.api_media_stats, name="api_media_stats"),
    path("api/media/movies/", views.api_media_movies, name="api_media_movies"),
    path("api/media/series/", views.api_media_series, name="api_media_series"),
    path("api/media/anime/", views.api_media_anime, name="api_media_anime"),
]
