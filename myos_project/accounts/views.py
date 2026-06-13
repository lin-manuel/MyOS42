from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .device_utils import generate_device_fingerprint, get_client_ip
from .forms import LoginForm, PasswordResetConfirmForm, PasswordResetRequestForm
from .models import LoginActivity, TrustedDevice, User
from .otp_utils import generate_otp, send_verification_email, store_otp, verify_otp


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _json_error(message, status=400):
    return JsonResponse({"ok": False, "error": message}, status=status)


def _json_ok(payload=None):
    data = {"ok": True}
    if payload:
        data.update(payload)
    return JsonResponse(data)


def _first_form_error(form, fallback="Invalid input."):
    for errors in form.errors.values():
        if errors:
            return errors[0]
    return fallback


def _is_rate_limited(request, key_prefix, max_attempts=None, window_seconds=None):
    """Returns True if this IP has exceeded max_attempts in the time window."""
    max_attempts = max_attempts if max_attempts is not None else getattr(settings, "LOGIN_RATE_LIMIT_ATTEMPTS", 10)
    window_seconds = window_seconds if window_seconds is not None else getattr(settings, "LOGIN_RATE_LIMIT_WINDOW_SECONDS", 300)
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown")).split(",")[0].strip()
    cache_key = f"ratelimit:{key_prefix}:{ip}"
    attempts = cache.get(cache_key, 0)
    if attempts >= max_attempts:
        return True
    cache.set(cache_key, attempts + 1, timeout=window_seconds)
    return False


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        ip = get_client_ip(request)
        fingerprint = generate_device_fingerprint(request)
        email_attempt = (request.POST.get("email") or "").strip().lower() or "anonymous"
        max_attempts = getattr(settings, "LOGIN_RATE_LIMIT_ATTEMPTS", 10)
        window_seconds = getattr(settings, "LOGIN_RATE_LIMIT_WINDOW_SECONDS", 300)

        if _is_rate_limited(request, f"login-email:{email_attempt}", max_attempts=max_attempts, window_seconds=window_seconds) or _is_rate_limited(
            request,
            "login-ip",
            max_attempts=max_attempts,
            window_seconds=window_seconds,
        ):
            LoginActivity.objects.create(
                email_attempted=(request.POST.get("email") or "").strip().lower(),
                ip_address=ip,
                device_fingerprint=fingerprint,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                status="blocked",
                failure_reason="rate_limited",
            )
            window_minutes = max(1, round(window_seconds / 60))
            if _is_ajax(request):
                return JsonResponse(
                    {"ok": False, "error": f"Too many login attempts. Please wait {window_minutes} minutes."},
                    status=429,
                )
            messages.error(request, f"Too many login attempts. Please wait {window_minutes} minutes.")
            return render(request, "accounts/login.html", {"form": form}, status=429)

        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            password = form.cleaned_data["password"]
            remember_me = form.cleaned_data.get("remember_me", False)

            user = authenticate(request, username=email, password=password)

            if user is None:
                LoginActivity.objects.create(
                    email_attempted=email,
                    ip_address=ip,
                    device_fingerprint=fingerprint,
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    status="failed",
                    failure_reason="invalid_credentials",
                )
                if _is_ajax(request):
                    return _json_error("Invalid email or password.", status=401)
                messages.error(request, "Invalid email or password.")
                return render(request, "accounts/login.html", {"form": form})

            cache.delete(f"ratelimit:login-email:{email}")
            cache.delete(f"ratelimit:login-ip:{ip}")
            _complete_login(request, user, remember_me, ip, fingerprint)
            if _is_ajax(request):
                return _json_ok({"authenticated": True})
            return redirect("dashboard")
        if _is_ajax(request):
            return _json_error(_first_form_error(form))
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})


def _complete_login(request, user, remember_me, ip, fingerprint):
    login(request, user)
    if not remember_me:
        request.session.set_expiry(settings.SHORT_SESSION_AGE)
    else:
        request.session.set_expiry(settings.REMEMBER_ME_AGE)
    LoginActivity.objects.create(
        user=user,
        email_attempted=user.email,
        ip_address=ip,
        device_fingerprint=fingerprint,
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        status="success",
    )


@login_required
def logout_view(request):
    logout(request)
    if _is_ajax(request):
        return _json_ok({"logged_out": True})
    messages.success(request, "You have been signed out.")
    return redirect("accounts:login")


def password_reset_request_view(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            try:
                user = User.objects.get(email=email)
                otp = generate_otp()
                store_otp(email, otp)
                send_verification_email(email, otp, purpose="reset")
                request.session["reset_email"] = email
                if _is_ajax(request):
                    return _json_ok({"otp_required": True, "purpose": "reset", "email": email})
                messages.info(request, f"Reset code sent to {email}")
                return redirect("accounts:password_reset_confirm")
            except User.DoesNotExist:
                if _is_ajax(request):
                    return _json_ok({"otp_required": True})
                messages.info(
                    request, "If that email is registered, a reset code has been sent."
                )
        elif _is_ajax(request):
            return _json_error(_first_form_error(form))
    else:
        form = PasswordResetRequestForm()
    return render(request, "accounts/password_reset_request.html", {"form": form})


def password_reset_confirm_view(request):
    email = request.session.get("reset_email")
    if not email:
        if _is_ajax(request):
            return _json_error("No pending reset found.", status=400)
        return redirect("accounts:password_reset_request")

    if request.method == "POST":
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            if verify_otp(email, form.cleaned_data["otp"]):
                try:
                    user = User.objects.get(email=email)
                    user.set_password(form.cleaned_data["password1"])
                    user.save()
                    request.session.pop("reset_email", None)
                    if _is_ajax(request):
                        return _json_ok({"reset": True})
                    messages.success(request, "Password updated successfully. Please log in.")
                    return redirect("accounts:login")
                except User.DoesNotExist:
                    if _is_ajax(request):
                        return _json_error("User not found.", status=404)
                    messages.error(request, "User not found.")
            else:
                if _is_ajax(request):
                    return _json_error("Invalid or expired reset code.", status=400)
                messages.error(request, "Invalid or expired reset code.")
        elif _is_ajax(request):
            return _json_error(_first_form_error(form))
    else:
        form = PasswordResetConfirmForm()
    return render(
        request,
        "accounts/password_reset_confirm.html",
        {"form": form, "email": email},
    )


@login_required
def login_activity_view(request):
    activities = request.user.login_activity.all()[:5]
    trusted_devices = request.user.trusted_devices.all()
    return render(
        request,
        "accounts/login_activity.html",
        {"activities": activities, "trusted_devices": trusted_devices},
    )


@login_required
@require_POST
def remove_trusted_device_view(request, device_id):
    TrustedDevice.objects.filter(id=device_id, user=request.user).delete()
    if _is_ajax(request):
        return _json_ok({"removed": True})
    messages.success(request, "Trusted device removed.")
    return redirect("accounts:login_activity")
