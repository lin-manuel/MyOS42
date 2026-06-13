import random
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from apps.users.models import UserOTP

User = get_user_model()


class AuthService:
    @staticmethod
    def _generate_otp_code() -> str:
        return f"{random.randint(0, 999999):06d}"

    @classmethod
    def signup(cls, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            timezone=validated_data.get("timezone", "UTC"),
            is_active=True,
            is_email_verified=False,
        )
        cls.send_otp(user, "signup")
        return user

    @classmethod
    def send_otp(cls, user, purpose="signup"):
        code = cls._generate_otp_code()
        UserOTP.objects.create(
            user=user,
            purpose=purpose,
            code=code,
            expires_at=UserOTP.default_expiry(),
        )
        send_mail(
            subject=f"MyOS {purpose} verification code",
            message=f"Your verification code is: {code}",
            from_email=None,
            recipient_list=[user.email],
            fail_silently=True,
        )
        return code

    @staticmethod
    def verify_otp(email, code, purpose="signup"):
        user = User.objects.filter(email=email).first()
        if not user:
            return None
        otp = (
            UserOTP.objects.filter(user=user, code=code, purpose=purpose, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if not otp or otp.is_expired():
            return None
        otp.is_used = True
        otp.save(update_fields=["is_used", "updated_at"])
        if purpose == "signup":
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified", "updated_at"])
        return user

    @staticmethod
    def request_password_reset(email):
        user = User.objects.filter(email=email).first()
        if not user:
            return
        token = PasswordResetTokenGenerator().make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        send_mail(
            subject="MyOS Password Reset",
            message=f"Use this uid: {uid}\nUse this token: {token}",
            from_email=None,
            recipient_list=[email],
            fail_silently=True,
        )
