import random
import string

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

OTP_LENGTH = 6
OTP_PREFIX = "myos_otp_"


def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


def store_otp(email: str, otp: str):
    key = OTP_PREFIX + email.lower()
    cache.set(key, otp, timeout=settings.OTP_EXPIRY_SECONDS)


def verify_otp(email: str, submitted_otp: str) -> bool:
    key = OTP_PREFIX + email.lower()
    stored = cache.get(key)
    if stored and stored == submitted_otp.strip():
        cache.delete(key)
        return True
    return False


def send_verification_email(email: str, otp: str, purpose: str = "reset"):
    subjects = {
        "reset": "MyOS — Password reset code",
    }
    messages = {
        "reset": f"""
You requested a password reset for your MyOS account.

Your reset code is:

    {otp}

This code expires in 10 minutes.
If you did not request this, ignore this email.

— The MyOS Team
""",
    }
    send_mail(
        subject=subjects.get(purpose, "MyOS — Verification Code"),
        message=messages.get(purpose, f"Your code is: {otp}"),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
