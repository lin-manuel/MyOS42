from django.urls import path

from .views import (
    AppleSocialLoginAPIView,
    GoogleSocialLoginAPIView,
    PasswordResetConfirmAPIView,
    PasswordResetRequestAPIView,
    Request2FAAPIView,
    SecureTokenObtainPairView,
    SecureTokenRefreshView,
    SignupAPIView,
    Verify2FAAPIView,
    VerifyOTPAPIView,
)

urlpatterns = [
    path("auth/signup/", SignupAPIView.as_view(), name="signup"),
    path("auth/verify-otp/", VerifyOTPAPIView.as_view(), name="verify_otp"),
    path("auth/2fa/request/", Request2FAAPIView.as_view(), name="request_2fa"),
    path("auth/2fa/verify/", Verify2FAAPIView.as_view(), name="verify_2fa"),
    path("auth/token/", SecureTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", SecureTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/password-reset/request/", PasswordResetRequestAPIView.as_view(), name="password_reset_request"),
    path("auth/password-reset/confirm/", PasswordResetConfirmAPIView.as_view(), name="password_reset_confirm"),
    path("auth/social/google/", GoogleSocialLoginAPIView.as_view(), name="google_social_login"),
    path("auth/social/apple/", AppleSocialLoginAPIView.as_view(), name="apple_social_login"),
]
