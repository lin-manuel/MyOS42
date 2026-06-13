from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django_ratelimit.decorators import ratelimit
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    OTPVerifySerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    Request2FASerializer,
    SecureTokenObtainPairSerializer,
    SignupSerializer,
    UserSerializer,
)
from .services.auth_service import AuthService

User = get_user_model()


class SecureTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = SecureTokenObtainPairSerializer


class SecureTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class SignupAPIView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True))
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.signup(serializer.validated_data)
        return Response({"detail": "Signup created. Verify OTP sent to email.", "user_id": user.id}, status=201)


class VerifyOTPAPIView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True))
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.verify_otp(
            email=serializer.validated_data["email"],
            code=serializer.validated_data["code"],
            purpose="signup",
        )
        if not user:
            return Response({"detail": "Invalid or expired OTP"}, status=400)
        return Response({"detail": "OTP verified", "is_email_verified": user.is_email_verified})


class Request2FAAPIView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True))
    def post(self, request):
        serializer = Request2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if not user:
            return Response({"detail": "Invalid credentials"}, status=400)
        if not user.is_email_verified:
            return Response({"detail": "Verify email before requesting 2FA code"}, status=403)
        AuthService.send_otp(user, purpose="login_2fa")
        return Response({"detail": "2FA code sent"})


class Verify2FAAPIView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=True))
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AuthService.verify_otp(
            email=serializer.validated_data["email"],
            code=serializer.validated_data["code"],
            purpose="login_2fa",
        )
        if not user:
            return Response({"detail": "Invalid or expired 2FA code"}, status=400)
        return Response({"detail": "2FA verified"})


class PasswordResetRequestAPIView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True))
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.request_password_reset(serializer.validated_data["email"])
        return Response({"detail": "If account exists, reset instructions were sent."})


class PasswordResetConfirmAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=uid)
        except Exception:
            return Response({"detail": "Invalid reset payload"}, status=400)

        token = serializer.validated_data["token"]
        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({"detail": "Invalid token"}, status=400)

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return Response({"detail": "Password reset successful"})


class GoogleSocialLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("id_token")
        if not token:
            return Response({"detail": "id_token required"}, status=400)
        return Response({"detail": "Google social login is not configured on this server."}, status=503)


class AppleSocialLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("id_token")
        if not token:
            return Response({"detail": "id_token required"}, status=400)
        return Response({"detail": "Apple social login is not configured on this server."}, status=503)


class UserProfileViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        serializer = self.get_serializer(request.user)
        return Response({"user": serializer.data})
