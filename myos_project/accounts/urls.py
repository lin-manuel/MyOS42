from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password/reset/", views.password_reset_request_view, name="password_reset_request"),
    path("password/reset/confirm/", views.password_reset_confirm_view, name="password_reset_confirm"),
    path("security/activity/", views.login_activity_view, name="login_activity"),
    path(
        "security/devices/<int:device_id>/remove/",
        views.remove_trusted_device_view,
        name="remove_trusted_device",
    ),
]
