from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import UserOTP, UserProfile
from .services.auth_service import AuthService

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ("full_name", "avatar", "timezone", "currency", "country", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")


class UserSerializer(serializers.ModelSerializer):
    avatar_initials = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    profile = UserProfileSerializer(required=False)

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "avatar",
            "avatar_initials",
            "display_name",
            "timezone",
            "currency",
            "country",
            "preferences",
            "profile",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data is not None:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        return instance


class SignupSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    timezone = serializers.CharField(max_length=64, required=False, default="UTC")

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("Email already registered")
        return normalized


class Request2FASerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True, trim_whitespace=False)


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class SecureTokenObtainPairSerializer(TokenObtainPairSerializer):
    otp_code = serializers.CharField(max_length=6, required=False, allow_blank=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["is_email_verified"] = bool(user.is_email_verified)
        return token

    def validate(self, attrs):
        otp_code = (attrs.get("otp_code") or "").strip()
        data = super().validate(attrs)
        user = self.user

        if not user.is_email_verified:
            raise AuthenticationFailed("Verify your email before signing in.")

        if user.two_factor_enabled:
            if not otp_code:
                raise AuthenticationFailed("2FA code required.")
            verified_user = AuthService.verify_otp(
                email=user.email,
                code=otp_code,
                purpose="login_2fa",
            )
            if not verified_user or verified_user.pk != user.pk:
                raise AuthenticationFailed("Invalid or expired 2FA code.")

        return data


class UserOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserOTP
        fields = ("id", "purpose", "code", "expires_at", "is_used", "created_at")
        read_only_fields = fields
