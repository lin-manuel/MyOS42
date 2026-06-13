import csv
import json
import re
import base64
import hashlib
import hmac
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET, require_POST

from .forms import BucketGoalForm
from .models import (
    AcademicLevel,
    ApplicationDocument,
    ApplicationCost,
    BucketGoal,
    Budget,
    Category,
    ContactInfo,
    DigitalAccounts,
    DiaryEntry,
    ExamCertification,
    FinanceAlert,
    IdentityDocuments,
    IdentityUploadedFile,
    NotificationPreference,
    PageFormData,
    PasswordReferences,
    PersonalIdentityVault,
    Project,
    ProjectBudget,
    RecurringExpenseTemplate,
    SavingsGoal,
    Scholarship,
    ScholarshipApplication,
    ScholarshipRequirement,
    SocialProfiles,
    Task,
    Transaction,
    UploadedDocument,
    UserProfile,
)


ALLOWED_UPLOAD_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".doc",
    ".docx",
    ".txt",
}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
REMINDER_STORE_SLUG = "reminders_hub_data"
NOTIFICATION_CENTER_STATE_SLUG = "notification_center_state"
NOTIFICATION_PANEL_LIMIT = 6
DASHBOARD_IMAGE_DIR = settings.BASE_DIR / "myos_app" / "static" / "assets" / "dashboardimgs"
DASHBOARD_IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
TASK_PRIORITY_CHOICES = (
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
)
TASK_PRIORITY_LABELS = dict(TASK_PRIORITY_CHOICES)
REMINDER_CADENCE_CHOICES = (
    ("once", "One Time"),
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
)
REMINDER_CADENCE_LABELS = dict(REMINDER_CADENCE_CHOICES)
REMINDER_CHANNEL_CHOICES = (
    ("in_app", "In App"),
    ("email", "Email"),
    ("sms", "SMS"),
    ("whatsapp", "WhatsApp"),
)
REMINDER_CHANNEL_LABELS = dict(REMINDER_CHANNEL_CHOICES)
SEARCH_MIN_QUERY_LENGTH = getattr(settings, "SEARCH_MIN_QUERY_LENGTH", 2)
SEARCH_RESULT_LIMIT = getattr(settings, "SEARCH_RESULT_LIMIT", 20)
DIARY_PAGE_SIZE = getattr(settings, "DIARY_PAGE_SIZE", 20)
NOTIFICATION_CACHE_TTL = 60


def _is_htmx_request(request):
    return request.headers.get("HX-Request") == "true"


def _page_context(request, active_page, extra_context=None, notification_context=None):
    context = {
        "active_page": active_page,
    }
    context.update(notification_context or _notification_template_context(request, limit=NOTIFICATION_PANEL_LIMIT))
    if extra_context:
        context.update(extra_context)
    return context


def _dashboard_image_context():
    try:
        image_names = sorted(
            path.name
            for path in DASHBOARD_IMAGE_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in DASHBOARD_IMAGE_EXTENSIONS
        )
    except OSError:
        image_names = []

    if not image_names:
        return {"dashboard_hero_image": "assets/dashboard-illustration.svg"}

    return {
        "dashboard_hero_image": f"assets/dashboardimgs/{random.choice(image_names)}",
    }


def _render_page(
    request,
    template_name,
    active_page,
    extra_context=None,
    partial_template=None,
    notification_context=None,
    *,
    status=200,
    headers=None,
):
    # Ensure AJAX POST endpoints always have a CSRF cookie available in browser sessions.
    get_token(request)
    target_template = partial_template if _is_htmx_request(request) and partial_template else template_name
    response = render(
        request,
        target_template,
        _page_context(request, active_page, extra_context, notification_context=notification_context),
        status=status,
    )
    if headers:
        for key, value in headers.items():
            response[key] = value
    return response


def _require_finance_access(request):
    return None


def _require_education_access(request):
    return None


def _require_personal_vault_access(request):
    return None


def _clean_page_slug(page_slug):
    if not re.fullmatch(r"[a-z0-9_-]{2,50}", page_slug or ""):
        return None
    return page_slug


def _clean_field_key(field_key):
    if not re.fullmatch(r"[a-z0-9_-]{2,80}", field_key or ""):
        return None
    return field_key


def _upload_to_dict(upload):
    return {
        "id": upload.id,
        "page_slug": upload.page_slug,
        "field_key": upload.field_key,
        "label": upload.label,
        "original_name": upload.original_name,
        "content_type": upload.content_type,
        "file_size": upload.file_size,
        "url": upload.file.url if upload.file else "",
        "uploaded_at": upload.uploaded_at.isoformat(),
    }


def _truncate_text(value, limit=120):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _search_snippet(*parts, query="", limit=120):
    text = " ".join(str(part or "") for part in parts if str(part or "").strip())
    snippet = _truncate_text(text, limit=limit)
    if not query:
        return snippet
    lowered = snippet.lower()
    query_lower = query.lower()
    if query_lower not in lowered:
        return snippet
    start = max(0, lowered.find(query_lower) - 24)
    end = min(len(snippet), start + limit)
    return _truncate_text(snippet[start:end], limit=limit)


def _append_search_result(results, seen, *, result_type, icon, title, preview, url, group=None, score=0):
    key = (result_type, title, url)
    if key in seen:
        return
    seen.add(key)
    results.append(
        {
            "type": result_type,
            "group": group or result_type.replace("_", " ").title(),
            "icon": icon,
            "title": title,
            "preview": preview,
            "url": url,
            "score": score,
        }
    )


def _serialize_page_form_snapshot(snapshot):
    return {
        "page_slug": snapshot.page_slug,
        "data": snapshot.data or {},
        "updated_at": snapshot.updated_at.isoformat(),
    }


def _serialize_uploaded_document(item):
    return _upload_to_dict(item)


def home(request):
    return _render_page(
        request,
        "dashboard.html",
        "dashboard",
        _dashboard_image_context(),
        partial_template="dashboard_partial.html",
    )


def dashboard_page(request):
    return _render_page(
        request,
        "dashboard.html",
        "dashboard",
        _dashboard_image_context(),
        partial_template="dashboard_partial.html",
    )


def personal_page(request):
    return _render_page(request, "personal.html", "personal", partial_template="personal_partial.html")


def education_page(request):
    return _render_page(request, "education.html", "education", partial_template="education_partial.html")


def finance_page(request):
    return _render_page(request, "finance.html", "finance", partial_template="finance_partial.html")


def bucket_page(request):
    return bucket_list(request)


def projects_page(request):
    return _render_page(request, "projects.html", "projects", partial_template="projects_partial.html")


def diary_page(request):
    return _render_page(request, "diary.html", "diary", partial_template="diary_partial.html")


def reminders_page(request):
    return _render_page(request, "reminders.html", "reminders", partial_template="reminders_partial.html")


def calendar_page(request):
    return _render_page(request, "calendar.html", "calendar", partial_template="calendar_partial.html")


def notifications_page(request):
    notification_context = _notification_template_context(request, limit=None)
    return _render_page(
        request,
        "notifications.html",
        "notifications",
        {
            "notification_page_items": notification_context["notification_panel_items"],
            "notification_page_summary": notification_context["notification_summary"],
        },
        partial_template="notifications_partial.html",
        notification_context=notification_context,
    )


def settings_page(request):
    return _render_page(request, "settings.html", "settings", partial_template="settings_partial.html")


def _bucket_category_choices():
    return BucketGoal.CATEGORY_CHOICES


BUCKET_CATEGORY_ICONS = {
    "travel": "fa-plane-departure",
    "learning": "fa-book-open",
    "wealth": "fa-gem",
    "experiences": "fa-compass",
    "achievements": "fa-trophy",
}


def _normalize_bucket_category(value):
    if not value:
        return None
    normalized = value.strip().lower().replace(" ", "_")
    for slug, label in _bucket_category_choices():
        if normalized == slug or normalized == label.lower().replace(" ", "_"):
            return slug
    return None


def _bucket_category_counts():
    counts = {slug: 0 for slug, _ in _bucket_category_choices()}
    for row in BucketGoal.objects.values("category").annotate(total=Count("id")):
        counts[row["category"]] = row["total"]
    counts["all"] = sum(counts.values())
    return counts


def _bucket_summary():
    status_counts = {
        BucketGoal.STATUS_NOT_STARTED: 0,
        BucketGoal.STATUS_IN_PROGRESS: 0,
        BucketGoal.STATUS_COMPLETED: 0,
    }
    for row in BucketGoal.objects.values("status").annotate(total=Count("id")):
        status_counts[row["status"]] = row["total"]
    total = sum(status_counts.values())
    completed = status_counts[BucketGoal.STATUS_COMPLETED]
    return {
        "total": total,
        "completed": completed,
        "in_progress": status_counts[BucketGoal.STATUS_IN_PROGRESS],
        "not_started": status_counts[BucketGoal.STATUS_NOT_STARTED],
        "completion_rate": round((completed / total) * 100) if total else 0,
    }


def _serialize_bucket_goal(goal):
    return {
        "id": goal.id,
        "title": goal.title,
        "category": goal.category,
        "category_label": goal.get_category_display(),
        "description": goal.description,
        "target_year": goal.target_year,
        "estimated_cost": str(goal.estimated_cost) if goal.estimated_cost is not None else "",
        "status": goal.status,
        "status_label": goal.get_status_display(),
        "priority": goal.priority,
        "progress": goal.progress,
    }


def _wants_json(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")


def _bucket_redirect(request, category=None):
    target = request.POST.get("next") or request.GET.get("next") or request.META.get("HTTP_REFERER")
    if target:
        return redirect(target)
    if category:
        return redirect("bucket_category", category=category)
    return redirect("bucket_list")


def bucket_list(request):
    bucket_goals = BucketGoal.objects.all()
    counts = _bucket_category_counts()
    categories = [
        {"slug": slug, "label": label, "count": counts.get(slug, 0), "icon": BUCKET_CATEGORY_ICONS.get(slug, "fa-star")}
        for slug, label in _bucket_category_choices()
    ]
    return _render_page(
        request,
        "bucket.html",
        "bucket",
        {
            "bucket_goals": bucket_goals,
            "bucket_categories": categories,
            "category_counts": counts,
            "active_category": "all",
            "active_category_label": "All goals",
            "bucket_current_year": timezone.now().year,
            "bucket_summary": _bucket_summary(),
        },
        partial_template="bucket_partial.html",
    )


def bucket_category(request, category):
    category_slug = _normalize_bucket_category(category)
    if not category_slug:
        raise Http404("Unknown bucket category")
    bucket_goals = BucketGoal.objects.filter(category=category_slug)
    counts = _bucket_category_counts()
    categories = [
        {"slug": slug, "label": label, "count": counts.get(slug, 0), "icon": BUCKET_CATEGORY_ICONS.get(slug, "fa-star")}
        for slug, label in _bucket_category_choices()
    ]
    active_category_label = next((label for slug, label in _bucket_category_choices() if slug == category_slug), "Goals")
    return _render_page(
        request,
        "bucket.html",
        "bucket",
        {
            "bucket_goals": bucket_goals,
            "bucket_categories": categories,
            "category_counts": counts,
            "active_category": category_slug,
            "active_category_label": active_category_label,
            "bucket_current_year": timezone.now().year,
            "bucket_summary": _bucket_summary(),
        },
        partial_template="bucket_partial.html",
    )


@require_POST
def add_bucket_goal(request):
    form = BucketGoalForm(_request_data(request))
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        return _bucket_redirect(request)
    goal = form.save()
    if _wants_json(request):
        return JsonResponse({"ok": True, "goal": _serialize_bucket_goal(goal)}, status=201)
    return _bucket_redirect(request)


@require_POST
def edit_bucket_goal(request, id):
    goal = get_object_or_404(BucketGoal, id=id)
    payload = _request_data(request)
    if payload.get("action") == "complete":
        goal.status = BucketGoal.STATUS_COMPLETED
        goal.progress = 100
        goal.save(update_fields=["status", "progress", "updated_at"])
        if _wants_json(request):
            return JsonResponse({"ok": True, "goal": _serialize_bucket_goal(goal)})
        return _bucket_redirect(request)

    form = BucketGoalForm(payload, instance=goal)
    if not form.is_valid():
        if _wants_json(request):
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
        return _bucket_redirect(request)
    goal = form.save()
    if _wants_json(request):
        return JsonResponse({"ok": True, "goal": _serialize_bucket_goal(goal)})
    return _bucket_redirect(request)


@require_POST
def delete_bucket_goal(request, id):
    goal = get_object_or_404(BucketGoal, id=id)
    goal.delete()
    if _wants_json(request):
        return JsonResponse({"ok": True})
    return _bucket_redirect(request)


def _ensure_core_records():
    profile, _ = UserProfile.objects.get_or_create(
        id=1,
        defaults={
            "display_name": "",
            "email": "",
            "timezone": settings.TIME_ZONE,
        },
    )
    notifications, _ = NotificationPreference.objects.get_or_create(id=1)
    return profile, notifications


def _normalize_notification_center_state(data):
    payload = data if isinstance(data, dict) else {}
    read_ids = []
    for item in payload.get("read_ids", []):
        value = str(item or "").strip()
        if value:
            read_ids.append(value)
    return {
        "read_ids": sorted(set(read_ids)),
    }


def _notification_user_key(request):
    if getattr(request, "user", None) and request.user.is_authenticated:
        return f"user-{request.user.pk}"
    return "anon"


def _notification_state_slug(request):
    return f"{NOTIFICATION_CENTER_STATE_SLUG}:{_notification_user_key(request)}"


def _notification_cache_key(request, limit):
    limit_key = "all" if limit is None else str(limit)
    return f"notification-context:{_notification_user_key(request)}:{limit_key}"


def _invalidate_notification_context_cache(request):
    cache.delete_many(
        [
            _notification_cache_key(request, None),
            _notification_cache_key(request, NOTIFICATION_PANEL_LIMIT),
        ]
    )


def _get_notification_center_state(request):
    record, _ = PageFormData.objects.get_or_create(
        page_slug=_notification_state_slug(request),
        defaults={"data": {"read_ids": []}},
    )
    normalized = _normalize_notification_center_state(record.data)
    if normalized != record.data:
        record.data = normalized
        record.save(update_fields=["data", "updated_at"])
    return record, normalized


def _save_notification_center_state(record, state):
    normalized = _normalize_notification_center_state(state)
    record.data = normalized
    record.save(update_fields=["data", "updated_at"])
    return normalized


def _coerce_datetime(value, fallback=None):
    if isinstance(value, datetime):
        dt = value
    elif value:
        dt = parse_datetime(str(value))
    else:
        dt = None

    if dt is None:
        dt = fallback or timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _format_notification_time(dt):
    now = timezone.now()
    delta = now - dt
    if delta <= timedelta(minutes=1):
        return "Just now"
    if delta < timedelta(hours=1):
        minutes = max(1, int(delta.total_seconds() // 60))
        return f"{minutes} min ago"
    if delta < timedelta(hours=24):
        hours = max(1, int(delta.total_seconds() // 3600))
        return f"{hours} hr ago"
    if delta < timedelta(days=7):
        days = max(1, delta.days)
        return f"{days} day{'s' if days != 1 else ''} ago"
    return dt.strftime("%b %d, %I:%M %p")


def _notification_target(page_name, anchor=""):
    url = reverse(page_name)
    return f"{url}#{anchor}" if anchor else url


def _notification_tone_rank(tone):
    return {
        "critical": 0,
        "warning": 1,
        "info": 2,
    }.get(tone, 3)


def _build_notification_item(
    *,
    notification_id,
    source,
    source_label,
    title,
    message,
    url,
    icon,
    tone,
    created_at,
    is_read=False,
    chips=None,
):
    created_dt = _coerce_datetime(created_at)
    return {
        "id": notification_id,
        "source": source,
        "source_label": source_label,
        "title": title,
        "message": message,
        "url": url,
        "icon": icon,
        "tone": tone,
        "created_at": created_dt,
        "time_label": _format_notification_time(created_dt),
        "is_read": bool(is_read),
        "chips": chips or [],
        "mark_read_url": reverse("notifications_mark_read", args=[notification_id]),
    }


def _build_notification_feed(request, limit=None):
    _, reminder_store = _get_reminder_store()
    _, notification_state = _get_notification_center_state(request)
    local_read_ids = set(notification_state["read_ids"])
    today = date.today()
    items = []

    for alert in FinanceAlert.objects.all()[:40]:
        tone = "critical" if alert.severity == FinanceAlert.SEVERITY_CRITICAL else (
            "warning" if alert.severity == FinanceAlert.SEVERITY_WARNING else "info"
        )
        title = {
            FinanceAlert.TYPE_BUDGET_OVERRUN: "Budget pressure detected",
            FinanceAlert.TYPE_DEADLINE: "Finance deadline approaching",
            FinanceAlert.TYPE_CASHFLOW: "Cashflow signal",
            FinanceAlert.TYPE_GOAL_RISK: "Savings goal risk",
        }.get(alert.alert_type, "Finance notification")
        items.append(
            _build_notification_item(
                notification_id=f"finance-alert-{alert.id}",
                source="finance",
                source_label="Finance",
                title=title,
                message=alert.message,
                url=_notification_target("finance", "budget-alerts-list"),
                icon="fa-wallet",
                tone=tone,
                created_at=alert.created_at,
                is_read=alert.is_read,
                chips=[tone.title()],
            )
        )

    for task in Task.objects.all():
        meta = _normalize_task_meta(reminder_store["task_meta"].get(str(task.id)))
        due_date = _parse_date(meta.get("due_date"))
        if task.is_done or not due_date:
            continue
        days = (due_date - today).days
        if days < -14 or days > 14:
            continue
        tone = "critical" if days < 0 else "warning" if days <= 2 else "info"
        timing_copy = (
            "overdue"
            if days < 0
            else "due today"
            if days == 0
            else f"due in {days} day{'s' if days != 1 else ''}"
        )
        notification_id = f"task-{task.id}-{task.updated_at.strftime('%Y%m%d%H%M%S')}"
        items.append(
            _build_notification_item(
                notification_id=notification_id,
                source="tasks",
                source_label="Focus Tasks",
                title="Task timeline needs attention",
                message=f"{task.title} is {timing_copy}.",
                url=_notification_target("reminders", "reminders-focus-list"),
                icon="fa-list-check",
                tone=tone,
                created_at=task.updated_at,
                is_read=notification_id in local_read_ids,
                chips=[timing_copy.title()],
            )
        )

    for reminder in reminder_store["reminders"]:
        if reminder.get("is_completed"):
            continue
        reminder_date = _parse_date(reminder.get("reminder_date"))
        if not reminder_date:
            continue
        days = (reminder_date - today).days
        if days < -7 or days > 14:
            continue
        tone = "critical" if days < 0 else "warning" if days <= 2 else "info"
        timing_copy = (
            "overdue"
            if days < 0
            else "today"
            if days == 0
            else f"in {days} day{'s' if days != 1 else ''}"
        )
        timestamp = _coerce_datetime(reminder.get("updated_at"))
        notification_id = f"reminder-{reminder['id']}-{timestamp.strftime('%Y%m%d%H%M%S')}"
        details = (reminder.get("details") or "").strip()
        message = f"Scheduled {timing_copy}."
        if details:
            message = f"{message} {details}"
        items.append(
            _build_notification_item(
                notification_id=notification_id,
                source="reminders",
                source_label="Reminders",
                title=reminder.get("title") or "Scheduled reminder",
                message=message,
                url=_notification_target("reminders", "reminders-timeline"),
                icon="fa-bell",
                tone=tone,
                created_at=timestamp,
                is_read=notification_id in local_read_ids,
                chips=[
                    (reminder.get("category") or "Reminder").title(),
                    (reminder.get("channel") or "in_app").replace("_", " ").title(),
                ],
            )
        )

    for scholarship in Scholarship.objects.filter(is_active=True):
        if not scholarship.application_deadline:
            continue
        days = (scholarship.application_deadline - today).days
        if days < 0 or days > 45:
            continue
        tone = "warning" if days <= 14 else "info"
        notification_id = f"scholarship-{scholarship.id}-{scholarship.updated_at.strftime('%Y%m%d%H%M%S')}"
        items.append(
            _build_notification_item(
                notification_id=notification_id,
                source="education",
                source_label="Education",
                title="Scholarship deadline coming up",
                message=f"{scholarship.name} closes in {days} day{'s' if days != 1 else ''}.",
                url=_notification_target("education", "education-deadline-alerts"),
                icon="fa-graduation-cap",
                tone=tone,
                created_at=scholarship.updated_at,
                is_read=notification_id in local_read_ids,
                chips=["Deadline"],
            )
        )

    for document in ApplicationDocument.objects.exclude(expiration_date__isnull=True):
        days = (document.expiration_date - today).days
        if days < 0 or days > 30:
            continue
        tone = "warning" if days <= 7 else "info"
        notification_id = f"document-{document.id}-{document.updated_at.strftime('%Y%m%d%H%M%S')}"
        items.append(
            _build_notification_item(
                notification_id=notification_id,
                source="documents",
                source_label="Documents",
                title="Document expiry in range",
                message=f"{document.title} expires in {days} day{'s' if days != 1 else ''}.",
                url=_notification_target("education", "education-deadline-alerts"),
                icon="fa-file-lines",
                tone=tone,
                created_at=document.updated_at,
                is_read=notification_id in local_read_ids,
                chips=["Expiry"],
            )
        )

    items.sort(
        key=lambda item: (
            item["is_read"],
            _notification_tone_rank(item["tone"]),
            -item["created_at"].timestamp(),
        )
    )
    if limit is not None:
        items = items[:limit]
    return items


def _notification_summary(items):
    today_local = timezone.localdate()
    return {
        "total_count": len(items),
        "unread_count": sum(1 for item in items if not item["is_read"]),
        "attention_count": sum(1 for item in items if item["tone"] in {"warning", "critical"}),
        "today_count": sum(1 for item in items if timezone.localtime(item["created_at"]).date() == today_local),
    }


def _notification_template_context(request, limit=None):
    cache_key = _notification_cache_key(request, limit)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    all_items = _build_notification_feed(request, limit=None)
    items = all_items if limit is None else all_items[:limit]
    payload = {
        "notification_panel_items": items,
        "notification_summary": _notification_summary(all_items),
    }
    cache.set(cache_key, payload, timeout=NOTIFICATION_CACHE_TTL)
    return payload


def _mark_notification_as_read(request, notification_id):
    if notification_id.startswith("finance-alert-"):
        alert_id = notification_id.removeprefix("finance-alert-")
        if alert_id.isdigit():
            FinanceAlert.objects.filter(id=int(alert_id)).update(is_read=True)
        _invalidate_notification_context_cache(request)
        return

    record, state = _get_notification_center_state(request)
    read_ids = set(state["read_ids"])
    if notification_id not in read_ids:
        read_ids.add(notification_id)
        _save_notification_center_state(record, {"read_ids": sorted(read_ids)})
        _invalidate_notification_context_cache(request)


def _mark_all_notifications_as_read(request):
    current_items = _build_notification_feed(request, limit=None)
    FinanceAlert.objects.filter(is_read=False).update(is_read=True)
    record, state = _get_notification_center_state(request)
    read_ids = set(state["read_ids"])
    read_ids.update(item["id"] for item in current_items)
    _save_notification_center_state(record, {"read_ids": sorted(read_ids)})
    _invalidate_notification_context_cache(request)


def _parse_json(request):
    try:
        return json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return {}


def _request_data(request):
    if "application/json" in request.headers.get("Content-Type", ""):
        return _parse_json(request)
    return request.POST


def _validate_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return "No file was provided"
    if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        return "File is too large. Maximum size is 10MB"

    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        return "Unsupported file type"

    return None


def _normalize_task_priority(value):
    normalized = (value or "medium").strip().lower()
    return normalized if normalized in TASK_PRIORITY_LABELS else "medium"


def _default_task_meta():
    return {
        "notes": "",
        "focus_area": "",
        "due_date": "",
        "priority": "medium",
    }


def _normalize_task_meta(raw):
    meta = _default_task_meta()
    if isinstance(raw, dict):
        meta["notes"] = str(raw.get("notes") or "").strip()
        meta["focus_area"] = str(raw.get("focus_area") or "").strip()
        due_date = _parse_date(raw.get("due_date"))
        meta["due_date"] = due_date.isoformat() if due_date else ""
        meta["priority"] = _normalize_task_priority(raw.get("priority"))
    return meta


def _normalize_reminder_item(raw):
    item = raw if isinstance(raw, dict) else {}
    reminder_date = _parse_date(item.get("reminder_date")) or date.today()
    reminder_time = _parse_time(item.get("reminder_time"))
    cadence = (item.get("cadence") or "once").strip().lower()
    channel = (item.get("channel") or "in_app").strip().lower()
    if cadence not in REMINDER_CADENCE_LABELS:
        cadence = "once"
    if channel not in REMINDER_CHANNEL_LABELS:
        channel = "in_app"

    reminder_id = item.get("id")
    try:
        reminder_id = int(reminder_id)
    except (TypeError, ValueError):
        reminder_id = 0

    return {
        "id": reminder_id,
        "title": str(item.get("title") or "").strip(),
        "details": str(item.get("details") or "").strip(),
        "category": str(item.get("category") or "").strip(),
        "reminder_date": reminder_date.isoformat(),
        "reminder_time": reminder_time.isoformat(timespec="minutes") if reminder_time else "",
        "cadence": cadence,
        "channel": channel,
        "is_completed": _parse_bool(item.get("is_completed")),
        "is_pinned": _parse_bool(item.get("is_pinned")),
        "created_at": str(item.get("created_at") or datetime.utcnow().isoformat()),
        "updated_at": str(item.get("updated_at") or datetime.utcnow().isoformat()),
    }


def _normalize_reminder_store(data):
    payload = data if isinstance(data, dict) else {}
    reminders = payload.get("reminders")
    task_meta = payload.get("task_meta")
    if not isinstance(reminders, list):
        reminders = []
    if not isinstance(task_meta, dict):
        task_meta = {}
    return {
        "reminders": [_normalize_reminder_item(item) for item in reminders],
        "task_meta": {str(key): _normalize_task_meta(value) for key, value in task_meta.items()},
    }


def _get_reminder_store():
    record, _ = PageFormData.objects.get_or_create(
        page_slug=REMINDER_STORE_SLUG,
        defaults={"data": {"reminders": [], "task_meta": {}}},
    )
    normalized = _normalize_reminder_store(record.data)
    if record.data != normalized:
        record.data = normalized
        record.save(update_fields=["data", "updated_at"])
    return record, normalized


def _save_reminder_store(record, store):
    payload = _normalize_reminder_store(store)
    record.data = payload
    record.save(update_fields=["data", "updated_at"])
    return payload


def _task_due_state(task, task_meta=None, today=None):
    today = today or date.today()
    meta = _normalize_task_meta(task_meta)
    due_date = _parse_date(meta.get("due_date"))
    if task.is_done:
        return "completed"
    if not due_date:
        return "no_date"
    if due_date < today:
        return "overdue"
    if due_date == today:
        return "today"
    if due_date <= today + timedelta(days=7):
        return "upcoming"
    return "later"


def _task_due_label(task, task_meta=None, today=None):
    today = today or date.today()
    meta = _normalize_task_meta(task_meta)
    due_date = _parse_date(meta.get("due_date"))
    if task.is_done:
        return "Completed"
    if not due_date:
        return "No due date"
    if due_date < today:
        return f"Overdue by {(today - due_date).days} day(s)"
    if due_date == today:
        return "Due today"
    if due_date == today + timedelta(days=1):
        return "Due tomorrow"
    return f"Due {due_date.strftime('%b %d')}"


def _task_sort_key(task, task_meta_map):
    meta = _normalize_task_meta(task_meta_map.get(str(task.id)))
    state_order = {
        "overdue": 0,
        "today": 1,
        "upcoming": 2,
        "later": 3,
        "no_date": 4,
        "completed": 5,
    }
    priority_order = {"high": 0, "medium": 1, "low": 2}
    due_state = _task_due_state(task, meta)
    due_date = _parse_date(meta.get("due_date")) or date.max
    return (
        state_order.get(due_state, 6),
        priority_order.get(meta.get("priority"), 1),
        due_date,
        task.sort_order,
        task.id,
    )


def _task_to_dict(task, task_meta_map=None):
    meta_map = task_meta_map or {}
    meta = _normalize_task_meta(meta_map.get(str(task.id)))
    return {
        "id": task.id,
        "title": task.title,
        "notes": meta["notes"],
        "focus_area": meta["focus_area"],
        "due_date": meta["due_date"] or None,
        "priority": meta["priority"],
        "priority_label": TASK_PRIORITY_LABELS.get(meta["priority"], "Medium"),
        "due_state": _task_due_state(task, meta),
        "due_label": _task_due_label(task, meta),
        "is_done": task.is_done,
        "sort_order": task.sort_order,
    }


def _reminder_due_state(reminder, today=None):
    today = today or date.today()
    reminder_date = _parse_date(reminder.get("reminder_date")) or today
    if reminder.get("is_completed"):
        return "completed"
    if reminder_date < today:
        return "overdue"
    if reminder_date == today:
        return "today"
    if reminder_date <= today + timedelta(days=7):
        return "upcoming"
    return "later"


def _reminder_scheduled_label(reminder):
    reminder_date = _parse_date(reminder.get("reminder_date")) or date.today()
    reminder_time = _parse_time(reminder.get("reminder_time"))
    if reminder_time:
        return f"{reminder_date.strftime('%b %d')} at {reminder_time.strftime('%I:%M %p').lstrip('0')}"
    return reminder_date.strftime("%b %d")


def _reminder_due_label(reminder, today=None):
    today = today or date.today()
    reminder_date = _parse_date(reminder.get("reminder_date")) or today
    if reminder.get("is_completed"):
        return "Completed"
    if reminder_date < today:
        return f"Missed {(today - reminder_date).days} day(s) ago"
    if reminder_date == today:
        return "Scheduled for today"
    if reminder_date == today + timedelta(days=1):
        return "Scheduled tomorrow"
    return f"Scheduled {reminder_date.strftime('%b %d')}"


def _reminder_sort_key(reminder):
    state_order = {
        "overdue": 0,
        "today": 1,
        "upcoming": 2,
        "later": 3,
        "completed": 4,
    }
    reminder_date = _parse_date(reminder.get("reminder_date")) or date.max
    reminder_time = _parse_time(reminder.get("reminder_time")) or datetime.max.time()
    return (
        0 if reminder.get("is_pinned") else 1,
        state_order.get(_reminder_due_state(reminder), 5),
        reminder_date,
        reminder_time,
        reminder.get("id") or 0,
    )


def _reminder_to_dict(reminder):
    item = _normalize_reminder_item(reminder)
    return {
        "id": item["id"],
        "title": item["title"],
        "details": item["details"],
        "category": item["category"],
        "reminder_date": item["reminder_date"],
        "reminder_time": item["reminder_time"] or None,
        "cadence": item["cadence"],
        "cadence_label": REMINDER_CADENCE_LABELS.get(item["cadence"], "One Time"),
        "channel": item["channel"],
        "channel_label": REMINDER_CHANNEL_LABELS.get(item["channel"], "In App"),
        "scheduled_label": _reminder_scheduled_label(item),
        "due_state": _reminder_due_state(item),
        "due_label": _reminder_due_label(item),
        "is_completed": item["is_completed"],
        "is_pinned": item["is_pinned"],
        "updated_at": item["updated_at"],
    }


def _build_reminders_overview():
    today = date.today()
    _, store = _get_reminder_store()
    task_meta_map = store["task_meta"]
    all_tasks = list(Task.objects.all())
    all_reminders = [_normalize_reminder_item(item) for item in store["reminders"]]

    focus_tasks = sorted(all_tasks, key=lambda task: _task_sort_key(task, task_meta_map))
    open_tasks = [task for task in all_tasks if not task.is_done]
    active_reminders = sorted((item for item in all_reminders if not item["is_completed"]), key=_reminder_sort_key)
    completed_reminders = [item for item in all_reminders if item["is_completed"]]

    overdue_total = sum(
        1 for task in open_tasks if _task_due_state(task, task_meta_map.get(str(task.id)), today) == "overdue"
    )
    overdue_total += sum(1 for item in active_reminders if _reminder_due_state(item, today) == "overdue")

    due_today_total = sum(
        1 for task in open_tasks if _task_due_state(task, task_meta_map.get(str(task.id)), today) == "today"
    )
    due_today_total += sum(1 for item in active_reminders if _reminder_due_state(item, today) == "today")

    this_week_total = sum(
        1
        for task in open_tasks
        if (
            _parse_date(_normalize_task_meta(task_meta_map.get(str(task.id))).get("due_date"))
            and today <= _parse_date(_normalize_task_meta(task_meta_map.get(str(task.id))).get("due_date")) <= today + timedelta(days=7)
        )
    )
    this_week_total += sum(
        1
        for item in active_reminders
        if today <= (_parse_date(item.get("reminder_date")) or today) <= today + timedelta(days=7)
    )

    completed_total = sum(1 for task in all_tasks if task.is_done) + len(completed_reminders)
    active_total = len(open_tasks) + len(active_reminders)
    grand_total = completed_total + active_total
    completion_rate = round((completed_total / grand_total) * 100) if grand_total else 0

    next_delivery = active_reminders[0] if active_reminders else None

    channels = []
    for channel, label in REMINDER_CHANNEL_CHOICES:
        count = sum(1 for item in all_reminders if item["channel"] == channel)
        if count:
            channels.append({"channel": channel, "label": label, "count": count})

    cadence = []
    for cadence_key, label in REMINDER_CADENCE_CHOICES:
        count = sum(1 for item in all_reminders if item["cadence"] == cadence_key)
        if count:
            cadence.append({"cadence": cadence_key, "label": label, "count": count})

    return {
        "summary": {
            "due_today_count": due_today_total,
            "overdue_count": overdue_total,
            "this_week_count": this_week_total,
            "focus_open_count": len(open_tasks),
            "focus_done_count": sum(1 for task in all_tasks if task.is_done),
            "completed_count": completed_total,
            "completion_rate": completion_rate,
            "next_delivery": _reminder_scheduled_label(next_delivery) if next_delivery else "Nothing queued",
        },
        "tasks": [_task_to_dict(task, task_meta_map) for task in focus_tasks],
        "focus_tasks": [_task_to_dict(task, task_meta_map) for task in focus_tasks[:8]],
        "all_reminders": [_reminder_to_dict(item) for item in sorted(all_reminders, key=_reminder_sort_key)],
        "upcoming_reminders": [_reminder_to_dict(item) for item in active_reminders[:8]],
        "completed_reminders": [_reminder_to_dict(item) for item in sorted(completed_reminders, key=lambda item: item.get("updated_at", ""), reverse=True)[:6]],
        "agenda": [_reminder_to_dict(item) for item in active_reminders[:5]],
        "channels": channels,
        "cadence": cadence,
    }


def _entry_to_dict(entry):
    return {
        "id": entry.id,
        "entry_date": entry.entry_date.isoformat(),
        "mood": entry.mood,
        "content": entry.content,
        "achievements": entry.achievements,
        "lessons": entry.lessons,
        "ideas": entry.ideas,
        "created_at": entry.created_at.isoformat(),
    }


def _compute_diary_streak(window_days=90):
    """Returns diary streak stats and activity for the last N days."""
    today = date.today()
    start_date = today - timedelta(days=max(window_days - 1, 0))
    entries = DiaryEntry.objects.filter(entry_date__gte=start_date).values_list("entry_date", flat=True)
    entry_set = set(entries)

    streak = 0
    check = today
    while check in entry_set:
        streak += 1
        check -= timedelta(days=1)

    longest = 0
    run = 0
    days = []
    for offset in range(window_days - 1, -1, -1):
        current_day = today - timedelta(days=offset)
        has_entry = current_day in entry_set
        if has_entry:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
        days.append(
            {
                "date": current_day.isoformat(),
                "has_entry": has_entry,
            }
        )

    return {
        "current_streak": streak,
        "longest_streak": longest,
        "total_entries": DiaryEntry.objects.count(),
        "days": days,
    }


@require_GET
def global_search(request):
    query = (request.GET.get("q") or "").strip()
    if len(query) < SEARCH_MIN_QUERY_LENGTH:
        return JsonResponse({"ok": True, "results": []})

    lower_query = query.lower()
    results = []
    seen = set()
    diary_url = reverse("diary")
    reminders_url = reverse("reminders")
    finance_url = reverse("finance")
    projects_url = reverse("projects")
    education_url = reverse("education")
    bucket_url = reverse("bucket")

    diary_qs = DiaryEntry.objects.filter(
        Q(content__icontains=query)
        | Q(mood__icontains=query)
        | Q(achievements__icontains=query)
        | Q(lessons__icontains=query)
        | Q(ideas__icontains=query)
    ).order_by("-entry_date", "-id")[:5]
    for entry in diary_qs:
        preview = _search_snippet(entry.content, entry.achievements, entry.lessons, entry.ideas, query=query)
        _append_search_result(
            results,
            seen,
            result_type="diary",
            group="Diary",
            icon="fa-book-open",
            title=f"Diary — {entry.entry_date.strftime('%b %d, %Y')}",
            preview=preview or _truncate_text(entry.content or entry.achievements or entry.lessons or entry.ideas or "Journal entry"),
            url=diary_url,
            score=5,
        )
        if len(results) >= SEARCH_RESULT_LIMIT:
            return JsonResponse({"ok": True, "results": results[:SEARCH_RESULT_LIMIT]})

    _, reminder_store = _get_reminder_store()
    task_meta_map = reminder_store["task_meta"]
    for task in Task.objects.all():
        meta = _normalize_task_meta(task_meta_map.get(str(task.id)))
        searchable = " ".join(
            [
                task.title,
                meta.get("notes", ""),
                meta.get("focus_area", ""),
                meta.get("due_date", ""),
                meta.get("priority", ""),
            ]
        ).lower()
        if lower_query not in searchable:
            continue
        preview = _search_snippet(meta.get("focus_area"), meta.get("notes"), meta.get("due_date"), query=query)
        if not preview:
            preview = "Focus task" + (" — Done" if task.is_done else " — Open")
        _append_search_result(
            results,
            seen,
            result_type="task",
            group="Tasks",
            icon="fa-list-check",
            title=task.title,
            preview=preview,
            url=reminders_url,
            score=4,
        )
        if len(results) >= SEARCH_RESULT_LIMIT:
            return JsonResponse({"ok": True, "results": results[:SEARCH_RESULT_LIMIT]})

    for reminder in reminder_store["reminders"]:
        reminder_blob = " ".join(
            [
                str(reminder.get("title") or ""),
                str(reminder.get("details") or ""),
                str(reminder.get("category") or ""),
                str(reminder.get("cadence") or ""),
                str(reminder.get("channel") or ""),
                str(reminder.get("reminder_date") or ""),
                str(reminder.get("reminder_time") or ""),
            ]
        ).lower()
        if lower_query not in reminder_blob:
            continue
        preview = _search_snippet(reminder.get("details"), reminder.get("category"), reminder.get("reminder_date"), query=query)
        _append_search_result(
            results,
            seen,
            result_type="reminder",
            group="Reminders",
            icon="fa-bell",
            title=str(reminder.get("title") or "Scheduled reminder"),
            preview=preview or reminder.get("reminder_date", ""),
            url=reminders_url,
            score=4,
        )
        if len(results) >= SEARCH_RESULT_LIMIT:
            return JsonResponse({"ok": True, "results": results[:SEARCH_RESULT_LIMIT]})

    for tx in Transaction.objects.select_related("category"):
        searchable = " ".join(
            [
                tx.description,
                tx.notes,
                tx.category.name,
                tx.category.slug,
                " ".join(tx.tags or []),
                tx.account,
                tx.tx_type,
            ]
        ).lower()
        if lower_query not in searchable:
            continue
        preview = f"KES {tx.amount:,.2f} — {tx.tx_date.strftime('%b %d, %Y')}"
        if tx.notes:
            preview = _search_snippet(tx.notes, tx.category.name, query=query) or preview
        _append_search_result(
            results,
            seen,
            result_type="finance",
            group="Finance",
            icon="fa-wallet",
            title=tx.description,
            preview=preview,
            url=finance_url,
            score=3,
        )
        if len(results) >= SEARCH_RESULT_LIMIT:
            return JsonResponse({"ok": True, "results": results[:SEARCH_RESULT_LIMIT]})

    for project in Project.objects.all():
        searchable = " ".join([project.title, project.description or "", project.get_status_display()]).lower()
        if lower_query not in searchable:
            continue
        preview = _search_snippet(project.description or project.get_status_display(), query=query)
        _append_search_result(
            results,
            seen,
            result_type="project",
            group="Projects",
            icon="fa-rocket",
            title=project.title,
            preview=preview or project.get_status_display(),
            url=projects_url,
            score=3,
        )
        if len(results) >= SEARCH_RESULT_LIMIT:
            return JsonResponse({"ok": True, "results": results[:SEARCH_RESULT_LIMIT]})

    for scholarship in Scholarship.objects.all():
        searchable = " ".join(
            [
                scholarship.name,
                scholarship.country,
                scholarship.university,
                scholarship.field_of_study,
                scholarship.degree_level,
                scholarship.official_website,
                scholarship.other_benefits,
            ]
        ).lower()
        if lower_query not in searchable:
            continue
        preview = _search_snippet(
            scholarship.country,
            scholarship.university,
            scholarship.field_of_study,
            scholarship.degree_level,
            query=query,
        )
        _append_search_result(
            results,
            seen,
            result_type="scholarship",
            group="Education",
            icon="fa-graduation-cap",
            title=scholarship.name,
            preview=preview or f"{scholarship.country} — {scholarship.field_of_study}",
            url=education_url,
            score=2,
        )
        if len(results) >= SEARCH_RESULT_LIMIT:
            return JsonResponse({"ok": True, "results": results[:SEARCH_RESULT_LIMIT]})

    for goal in BucketGoal.objects.all():
        searchable = " ".join([goal.title, goal.description or "", goal.get_category_display(), goal.get_status_display()]).lower()
        if lower_query not in searchable:
            continue
        preview = _search_snippet(goal.description, goal.get_category_display(), goal.get_status_display(), query=query)
        _append_search_result(
            results,
            seen,
            result_type="bucket",
            group="Bucket List",
            icon="fa-star",
            title=goal.title,
            preview=preview or f"{goal.get_category_display()} — {goal.get_status_display()}",
            url=bucket_url,
            score=2,
        )
        if len(results) >= SEARCH_RESULT_LIMIT:
            return JsonResponse({"ok": True, "results": results[:SEARCH_RESULT_LIMIT]})

    results.sort(key=lambda item: (-item.get("score", 0), item["group"], item["title"].lower()))
    return JsonResponse({"ok": True, "results": results[:SEARCH_RESULT_LIMIT]})


@require_GET
def calendar_events(request):
    today = date.today()
    try:
        year = int(request.GET.get("year", today.year))
    except (TypeError, ValueError):
        year = today.year
    try:
        month = int(request.GET.get("month", today.month))
    except (TypeError, ValueError):
        month = today.month

    if month < 1 or month > 12:
        month = today.month

    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    events = []
    _, store = _get_reminder_store()

    for task in Task.objects.all():
        meta = _normalize_task_meta(store["task_meta"].get(str(task.id)))
        due = _parse_date(meta.get("due_date"))
        if due and start <= due < end:
            events.append(
                {
                    "id": f"task-{task.id}",
                    "type": "task",
                    "title": task.title,
                    "date": due.isoformat(),
                    "is_done": task.is_done,
                    "priority": meta.get("priority", "medium"),
                    "color": "#4ADE80" if task.is_done else "#6C63FF",
                    "url": reverse("reminders"),
                }
            )

    for reminder in store["reminders"]:
        reminder_date = _parse_date(reminder.get("reminder_date"))
        if reminder_date and start <= reminder_date < end:
            events.append(
                {
                    "id": f"reminder-{reminder['id']}",
                    "type": "reminder",
                    "title": reminder.get("title", ""),
                    "date": reminder_date.isoformat(),
                    "is_done": reminder.get("is_completed", False),
                    "channel": reminder.get("channel", "in_app"),
                    "color": "#E8B84B",
                    "url": reverse("reminders"),
                }
            )

    for scholarship in Scholarship.objects.filter(is_active=True):
        if scholarship.application_deadline and start <= scholarship.application_deadline < end:
            events.append(
                {
                    "id": f"scholarship-{scholarship.id}",
                    "type": "deadline",
                    "title": f"Deadline: {scholarship.name}",
                    "date": scholarship.application_deadline.isoformat(),
                    "color": "#FF6B6B",
                    "url": reverse("education"),
                }
            )

    for cost in ApplicationCost.objects.exclude(deadline__isnull=True):
        if start <= cost.deadline < end:
            events.append(
                {
                    "id": f"appcost-{cost.id}",
                    "type": "deadline",
                    "title": f"Payment: {cost.get_item_type_display()}",
                    "date": cost.deadline.isoformat(),
                    "color": "#F87171",
                    "url": reverse("finance"),
                }
            )

    for goal in BucketGoal.objects.exclude(target_year__isnull=True):
        target_date = date(goal.target_year, 12, 31)
        if start <= target_date < end:
            events.append(
                {
                    "id": f"bucket-{goal.id}",
                    "type": "bucket",
                    "title": f"Bucket target: {goal.title}",
                    "date": target_date.isoformat(),
                    "color": "#22D3EE",
                    "url": reverse("bucket"),
                }
            )

    return JsonResponse({"ok": True, "events": events, "year": year, "month": month})


@require_GET
def bootstrap_data(request):
    profile, notifications = _ensure_core_records()
    _, store = _get_reminder_store()
    tasks = [_task_to_dict(task, store["task_meta"]) for task in Task.objects.all()]
    diary_entries = [_entry_to_dict(entry) for entry in DiaryEntry.objects.all()[:12]]
    reminders_overview = _build_reminders_overview()
    streak_data = _compute_diary_streak()
    return JsonResponse(
        {
            "ok": True,
            "profile": {
                "display_name": profile.display_name,
                "email": profile.email,
                "timezone": profile.timezone,
            },
            "notifications": {
                "scholarship_deadlines": notifications.scholarship_deadlines,
                "task_due_alerts": notifications.task_due_alerts,
                "diary_prompt": notifications.diary_prompt,
                "finance_alerts": notifications.finance_alerts,
            },
            "tasks": tasks,
            "diary_entries": diary_entries,
            "diary_streak": {
                "current_streak": streak_data["current_streak"],
                "total_entries": streak_data["total_entries"],
            },
            "reminders_summary": reminders_overview["summary"],
        }
    )


@require_POST
def toggle_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.is_done = not task.is_done
    task.save(update_fields=["is_done", "updated_at"])
    _, store = _get_reminder_store()
    return JsonResponse({"ok": True, "task": _task_to_dict(task, store["task_meta"])})


@require_POST
def create_task(request):
    payload = _parse_json(request)
    title = (payload.get("title") or "").strip()
    if not title:
        return JsonResponse({"ok": False, "error": "Task title is required"}, status=400)

    max_order = Task.objects.order_by("-sort_order").values_list("sort_order", flat=True).first() or 0
    task = Task.objects.create(title=title, sort_order=max_order + 1)

    record, store = _get_reminder_store()
    store["task_meta"][str(task.id)] = _normalize_task_meta(
        {
            "notes": payload.get("notes"),
            "focus_area": payload.get("focus_area"),
            "due_date": payload.get("due_date"),
            "priority": payload.get("priority"),
        }
    )
    store = _save_reminder_store(record, store)
    return JsonResponse({"ok": True, "task": _task_to_dict(task, store["task_meta"])}, status=201)


@require_GET
def reminders_bootstrap(request):
    return JsonResponse({"ok": True, **_build_reminders_overview()})


@require_POST
def reminders_create(request):
    payload = _parse_json(request)
    title = (payload.get("title") or "").strip()
    if not title:
        return _json_error("Reminder title is required")

    record, store = _get_reminder_store()
    next_id = max((item.get("id") or 0) for item in store["reminders"]) + 1 if store["reminders"] else 1
    reminder = _normalize_reminder_item(
        {
            "id": next_id,
            "title": title,
            "details": payload.get("details") or payload.get("notes"),
            "category": payload.get("category"),
            "reminder_date": payload.get("reminder_date"),
            "reminder_time": payload.get("reminder_time"),
            "cadence": payload.get("cadence"),
            "channel": payload.get("channel"),
            "is_completed": False,
            "is_pinned": _parse_bool(payload.get("is_pinned")),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
    )
    store["reminders"].append(reminder)
    _save_reminder_store(record, store)
    return JsonResponse({"ok": True, "reminder": _reminder_to_dict(reminder)}, status=201)


@require_POST
def reminders_update(request, reminder_id):
    record, store = _get_reminder_store()
    target = None
    for reminder in store["reminders"]:
        if reminder.get("id") == reminder_id:
            target = reminder
            break
    if target is None:
        return _json_error("Reminder not found", status=404)

    payload = _parse_json(request)

    if "title" in payload:
        title = (payload.get("title") or "").strip()
        if not title:
            return _json_error("Reminder title is required")
        target["title"] = title

    if "details" in payload or "notes" in payload:
        target["details"] = (payload.get("details") or payload.get("notes") or "").strip()

    if "category" in payload:
        target["category"] = (payload.get("category") or "").strip()

    if "reminder_date" in payload:
        parsed_date = _parse_date(payload.get("reminder_date"))
        if payload.get("reminder_date") and parsed_date is None:
            return _json_error("Reminder date is invalid")
        if parsed_date is not None:
            target["reminder_date"] = parsed_date.isoformat()

    if "reminder_time" in payload:
        if payload.get("reminder_time"):
            parsed_time = _parse_time(payload.get("reminder_time"))
            if parsed_time is None:
                return _json_error("Reminder time is invalid")
            target["reminder_time"] = parsed_time.isoformat(timespec="minutes")
        else:
            target["reminder_time"] = ""

    if "cadence" in payload:
        cadence = (payload.get("cadence") or "once").strip().lower()
        if cadence not in REMINDER_CADENCE_LABELS:
            return _json_error("Reminder cadence is invalid")
        target["cadence"] = cadence

    if "channel" in payload:
        channel = (payload.get("channel") or "in_app").strip().lower()
        if channel not in REMINDER_CHANNEL_LABELS:
            return _json_error("Reminder channel is invalid")
        target["channel"] = channel

    if "is_completed" in payload:
        target["is_completed"] = _parse_bool(payload.get("is_completed"))

    if "is_pinned" in payload:
        target["is_pinned"] = _parse_bool(payload.get("is_pinned"))

    target["updated_at"] = datetime.utcnow().isoformat()
    store = _save_reminder_store(record, store)
    updated = next((item for item in store["reminders"] if item.get("id") == reminder_id), target)
    return JsonResponse({"ok": True, "reminder": _reminder_to_dict(updated)})


@require_POST
def reminders_toggle(request, reminder_id):
    record, store = _get_reminder_store()
    target = None
    for reminder in store["reminders"]:
        if reminder.get("id") == reminder_id:
            target = reminder
            break
    if target is None:
        return _json_error("Reminder not found", status=404)
    target["is_completed"] = not _parse_bool(target.get("is_completed"))
    target["updated_at"] = datetime.utcnow().isoformat()
    store = _save_reminder_store(record, store)
    updated = next((item for item in store["reminders"] if item.get("id") == reminder_id), target)
    return JsonResponse({"ok": True, "reminder": _reminder_to_dict(updated)})


@require_POST
def reminders_delete(request, reminder_id):
    record, store = _get_reminder_store()
    original_count = len(store["reminders"])
    store["reminders"] = [item for item in store["reminders"] if item.get("id") != reminder_id]
    if len(store["reminders"]) == original_count:
        return _json_error("Reminder not found", status=404)
    _save_reminder_store(record, store)
    return JsonResponse({"ok": True})


@require_POST
def save_diary_entry(request):
    payload = _parse_json(request)
    entry = DiaryEntry.objects.create(
        entry_date=date.today(),
        mood=(payload.get("mood") or "").strip(),
        content=(payload.get("content") or "").strip(),
        achievements=(payload.get("achievements") or "").strip(),
        lessons=(payload.get("lessons") or "").strip(),
        ideas=(payload.get("ideas") or "").strip(),
    )
    return JsonResponse({"ok": True, "entry": _entry_to_dict(entry)}, status=201)


@require_GET
def diary_streak(request):
    return JsonResponse({"ok": True, **_compute_diary_streak()})


@require_GET
def diary_entries_list(request):
    page_size = DIARY_PAGE_SIZE
    try:
        page = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        requested_page_size = int(request.GET.get("page_size", page_size))
    except (TypeError, ValueError):
        requested_page_size = page_size
    page_size = max(1, min(requested_page_size, 100))
    qs = DiaryEntry.objects.all()
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)
    return JsonResponse(
        {
            "ok": True,
            "rows": [_entry_to_dict(entry) for entry in page_obj.object_list],
            "pagination": {
                "page": page_obj.number,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "total_items": paginator.count,
                "has_next": page_obj.has_next(),
                "has_prev": page_obj.has_previous(),
            },
        }
    )


@require_GET
def diary_export_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="myos-diary.csv"'
    writer = csv.writer(response)
    writer.writerow(["Date", "Mood", "Content", "Achievements", "Lessons", "Ideas", "Created At"])
    for entry in DiaryEntry.objects.all():
        writer.writerow(
            [
                entry.entry_date.isoformat(),
                entry.mood,
                entry.content,
                entry.achievements,
                entry.lessons,
                entry.ideas,
                entry.created_at.isoformat(),
            ]
        )
    return response


@require_GET
def full_data_export(request):
    """Export all user data as JSON for portability."""
    _, store = _get_reminder_store()
    profile, notifications = _ensure_core_records()
    vault, contact, identity_docs, social = _get_or_create_personal_vault()
    files = list(IdentityUploadedFile.objects.filter(vault=vault))
    digital_accounts = list(DigitalAccounts.objects.filter(vault=vault))
    password_refs = list(PasswordReferences.objects.filter(vault=vault))
    data = {
        "export_date": date.today().isoformat(),
        "profile": {
            "display_name": profile.display_name,
            "email": profile.email,
            "timezone": profile.timezone,
        },
        "notification_preferences": {
            "scholarship_deadlines": notifications.scholarship_deadlines,
            "task_due_alerts": notifications.task_due_alerts,
            "diary_prompt": notifications.diary_prompt,
            "finance_alerts": notifications.finance_alerts,
        },
        "tasks": [_task_to_dict(task, store["task_meta"]) for task in Task.objects.all()],
        "reminders": store["reminders"],
        "diary_entries": [_entry_to_dict(entry) for entry in DiaryEntry.objects.all()],
        "page_forms": [
            _serialize_page_form_snapshot(item)
            for item in PageFormData.objects.exclude(page_slug__in=[REMINDER_STORE_SLUG, NOTIFICATION_CENTER_STATE_SLUG])
        ],
        "uploads": [_upload_to_dict(item) for item in UploadedDocument.objects.all()],
        "bucket_goals": [_serialize_bucket_goal(goal) for goal in BucketGoal.objects.all()],
        "projects": [_serialize_project(project) for project in Project.objects.all()],
        "finance": {
            "categories": [_serialize_category(category) for category in Category.objects.all()],
            "budgets": [
                _serialize_budget(
                    budget,
                    _safe_decimal(
                        Transaction.objects.filter(
                            tx_type=Transaction.TYPE_EXPENSE,
                            category=budget.category,
                            tx_date__gte=budget.period_start,
                            tx_date__lt=_add_months(budget.period_start, 1),
                        ).aggregate(total=Sum("amount"))["total"]
                    ),
                )
                for budget in Budget.objects.select_related("category").all()
            ],
            "recurring_templates": [_serialize_recurring(template) for template in RecurringExpenseTemplate.objects.select_related("category").all()],
            "alerts": [_serialize_alert(item) for item in FinanceAlert.objects.all()],
        },
        "transactions": [
            _serialize_transaction(tx)
            for tx in Transaction.objects.all().select_related("category")
        ],
        "savings_goals": [],
        "education": {
            "academic_levels": [_serialize_academic_level(level) for level in AcademicLevel.objects.prefetch_related("exam_certifications").all()],
            "application_documents": [_serialize_application_document(item) for item in ApplicationDocument.objects.all()],
            "scholarships": [],
        },
        "personal_vault": {
            "identity": _serialize_personal_identity(vault),
            "contact": _serialize_contact_info(contact),
            "identity_documents": _serialize_identity_documents(identity_docs),
            "uploaded_files": [_serialize_identity_file(item) for item in files],
            "digital_accounts": [_serialize_digital_account(item) for item in digital_accounts],
            "social_profiles": _serialize_social_profiles(social),
            "password_references": [_serialize_password_reference(item) for item in password_refs],
        },
    }

    for goal in SavingsGoal.objects.all():
        tracked = _safe_decimal(
            Transaction.objects.filter(
                tx_type=Transaction.TYPE_SAVINGS,
                savings_goal=goal,
            ).aggregate(total=Sum("amount"))["total"]
        )
        current = goal.starting_amount + tracked
        suggestion = _compute_goal_suggestion(goal, current, date.today())
        data["savings_goals"].append(_serialize_savings_goal(goal, current, suggestion))

    scholarship_qs = Scholarship.objects.prefetch_related("requirements__linked_document").select_related("application")
    for scholarship in scholarship_qs:
        data["education"]["scholarships"].append(_serialize_scholarship(scholarship))

    response = HttpResponse(json.dumps(data, indent=2, default=str), content_type="application/json")
    response["Content-Disposition"] = 'attachment; filename="myos-export.json"'
    return response


@require_POST
def save_profile(request):
    payload = _parse_json(request)
    profile, _ = UserProfile.objects.get_or_create(id=1)
    profile.display_name = (payload.get("display_name") or profile.display_name).strip()
    profile.email = (payload.get("email") or profile.email).strip()
    profile.timezone = (payload.get("timezone") or profile.timezone).strip()
    profile.save()
    return JsonResponse({"ok": True})


@require_POST
def save_notifications(request):
    payload = _parse_json(request)
    prefs, _ = NotificationPreference.objects.get_or_create(id=1)
    prefs.scholarship_deadlines = bool(payload.get("scholarship_deadlines"))
    prefs.task_due_alerts = bool(payload.get("task_due_alerts"))
    prefs.diary_prompt = bool(payload.get("diary_prompt"))
    prefs.finance_alerts = bool(payload.get("finance_alerts"))
    prefs.save()
    return JsonResponse({"ok": True})


@require_GET
def notifications_feed(request):
    payload = _notification_template_context(request, limit=None)
    return JsonResponse(
        {
            "ok": True,
            "summary": payload["notification_summary"],
            "rows": [
                {
                    "id": item["id"],
                    "source": item["source"],
                    "source_label": item["source_label"],
                    "title": item["title"],
                    "message": item["message"],
                    "url": item["url"],
                    "icon": item["icon"],
                    "tone": item["tone"],
                    "time_label": item["time_label"],
                    "is_read": item["is_read"],
                    "chips": item["chips"],
                    "mark_read_url": item["mark_read_url"],
                    "created_at": item["created_at"].isoformat(),
                }
                for item in payload["notification_panel_items"]
            ],
        }
    )


@require_POST
def notifications_mark_read(request, notification_id):
    _mark_notification_as_read(request, notification_id)
    return JsonResponse({"ok": True, "id": notification_id})


@require_POST
def notifications_mark_all_read(request):
    _mark_all_notifications_as_read(request)
    return JsonResponse({"ok": True})


def _serialize_project(item):
    return {
        "id": item.id,
        "title": item.title,
        "description": item.description,
        "status": item.status,
        "progress": item.progress,
        "start_date": item.start_date.isoformat() if item.start_date else None,
        "end_date": item.end_date.isoformat() if item.end_date else None,
        "updated_at": item.updated_at.isoformat(),
    }


@require_GET
def projects_list(request):
    rows = [_serialize_project(item) for item in Project.objects.all()]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def projects_create(request):
    payload = _parse_json(request)
    title = (payload.get("title") or "").strip()
    if not title:
        return JsonResponse({"ok": False, "error": "Project title is required"}, status=400)

    status = (payload.get("status") or Project.STATUS_IDEA).strip()
    valid_statuses = {choice[0] for choice in Project.STATUS_CHOICES}
    if status not in valid_statuses:
        return JsonResponse({"ok": False, "error": "Invalid project status"}, status=400)

    try:
        progress = int(payload.get("progress", 0))
    except (TypeError, ValueError):
        progress = 0
    progress = max(0, min(100, progress))

    item = Project.objects.create(
        title=title,
        description=(payload.get("description") or "").strip(),
        status=status,
        progress=progress,
        start_date=_parse_date(payload.get("start_date")),
        end_date=_parse_date(payload.get("end_date")),
    )
    return JsonResponse({"ok": True, "project": _serialize_project(item)}, status=201)


@require_POST
def projects_update(request, project_id):
    item = get_object_or_404(Project, id=project_id)
    payload = _parse_json(request)

    title = (payload.get("title") or item.title).strip()
    if not title:
        return JsonResponse({"ok": False, "error": "Project title is required"}, status=400)

    status = (payload.get("status") or item.status).strip()
    valid_statuses = {choice[0] for choice in Project.STATUS_CHOICES}
    if status not in valid_statuses:
        return JsonResponse({"ok": False, "error": "Invalid project status"}, status=400)

    try:
        progress = int(payload.get("progress", item.progress))
    except (TypeError, ValueError):
        progress = item.progress
    progress = max(0, min(100, progress))

    item.title = title
    item.description = (payload.get("description") if "description" in payload else item.description or "").strip()
    item.status = status
    item.progress = progress
    if "start_date" in payload:
        item.start_date = _parse_date(payload.get("start_date"))
    if "end_date" in payload:
        item.end_date = _parse_date(payload.get("end_date"))
    item.save()
    return JsonResponse({"ok": True, "project": _serialize_project(item)})


@require_POST
def projects_delete(request, project_id):
    item = get_object_or_404(Project, id=project_id)
    item.delete()
    return JsonResponse({"ok": True})


@require_GET
def get_page_form_data(request, page_slug):
    clean_slug = _clean_page_slug(page_slug)
    if not clean_slug:
        return JsonResponse({"ok": False, "error": "Invalid page slug"}, status=400)

    snapshot, _ = PageFormData.objects.get_or_create(page_slug=clean_slug)
    return JsonResponse({"ok": True, "page": clean_slug, "data": snapshot.data or {}})


@require_POST
def save_page_form_data(request, page_slug):
    clean_slug = _clean_page_slug(page_slug)
    if not clean_slug:
        return JsonResponse({"ok": False, "error": "Invalid page slug"}, status=400)

    payload = _parse_json(request)
    data = payload.get("data")
    if not isinstance(data, dict):
        return JsonResponse({"ok": False, "error": "Expected object payload for data"}, status=400)

    snapshot, _ = PageFormData.objects.get_or_create(page_slug=clean_slug)
    snapshot.data = data
    snapshot.save(update_fields=["data", "updated_at"])
    return JsonResponse({"ok": True, "page": clean_slug, "updated_at": snapshot.updated_at.isoformat()})


@require_GET
def list_uploaded_files(request, page_slug):
    clean_slug = _clean_page_slug(page_slug)
    if not clean_slug:
        return JsonResponse({"ok": False, "error": "Invalid page slug"}, status=400)

    files = UploadedDocument.objects.filter(page_slug=clean_slug)
    field_key = request.GET.get("field_key", "").strip()
    if field_key:
        clean_field_key = _clean_field_key(field_key)
        if not clean_field_key:
            return JsonResponse({"ok": False, "error": "Invalid field key"}, status=400)
        files = files.filter(field_key=clean_field_key)

    return JsonResponse({"ok": True, "files": [_upload_to_dict(item) for item in files[:200]]})


@require_POST
def upload_file_for_field(request, page_slug, field_key):
    clean_slug = _clean_page_slug(page_slug)
    clean_field_key = _clean_field_key(field_key)
    if not clean_slug:
        return JsonResponse({"ok": False, "error": "Invalid page slug"}, status=400)
    if not clean_field_key:
        return JsonResponse({"ok": False, "error": "Invalid field key"}, status=400)

    uploaded_file = request.FILES.get("file")
    validation_error = _validate_uploaded_file(uploaded_file)
    if validation_error:
        return JsonResponse({"ok": False, "error": validation_error}, status=400)

    label = (request.POST.get("label") or "").strip()[:120]
    record = UploadedDocument.objects.create(
        page_slug=clean_slug,
        field_key=clean_field_key,
        label=label,
        file=uploaded_file,
        original_name=uploaded_file.name,
        content_type=(uploaded_file.content_type or "")[:120],
        file_size=uploaded_file.size,
    )
    return JsonResponse({"ok": True, "file": _upload_to_dict(record)}, status=201)


# -----------------------------
# Finance command center APIs
# -----------------------------


def _safe_decimal(value, default=Decimal("0.00")):
    if value in (None, ""):
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def _json_error(message, status=400):
    return JsonResponse({"ok": False, "error": message}, status=status)


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_time(value):
    if not value:
        return None
    for time_format in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(str(value), time_format).time()
        except ValueError:
            continue
    return None


def _to_money(value):
    return float(_safe_decimal(value))


def _month_bounds(any_date):
    start = any_date.replace(day=1)
    next_start = (start + timedelta(days=32)).replace(day=1)
    return start, next_start


def _month_key(any_date):
    return any_date.strftime("%Y-%m")


def _month_start(any_date):
    return any_date.replace(day=1)


def _add_months(any_date, months):
    month = any_date.month - 1 + months
    year = any_date.year + month // 12
    month = month % 12 + 1
    day = min(any_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def _split_tags(raw):
    if isinstance(raw, list):
        return [str(tag).strip() for tag in raw if str(tag).strip()][:20]
    if isinstance(raw, str):
        return [piece.strip() for piece in raw.split(",") if piece.strip()][:20]
    return []


def _serialize_category(category):
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "kind": category.kind,
        "color": category.color,
        "icon": category.icon,
        "is_active": category.is_active,
        "sort_order": category.sort_order,
    }


def _serialize_transaction(item):
    sign = Decimal("-1.00") if item.tx_type == Transaction.TYPE_EXPENSE else Decimal("1.00")
    signed_amount = sign * item.amount
    return {
        "id": item.id,
        "tx_date": item.tx_date.isoformat(),
        "description": item.description,
        "category": {
            "id": item.category_id,
            "name": item.category.name,
            "kind": item.category.kind,
            "color": item.category.color,
            "icon": item.category.icon,
        },
        "account": item.account,
        "tx_type": item.tx_type,
        "amount": _to_money(item.amount),
        "signed_amount": _to_money(signed_amount),
        "tags": item.tags or [],
        "notes": item.notes,
        "savings_goal_id": item.savings_goal_id,
        "application_cost_id": item.application_cost_id,
        "project_budget_id": item.project_budget_id,
        "updated_at": item.updated_at.isoformat(),
    }


def _serialize_budget(item, spent_amount):
    spent = _safe_decimal(spent_amount)
    remaining = item.monthly_limit - spent
    utilization = int((spent / item.monthly_limit) * 100) if item.monthly_limit > 0 else 0
    return {
        "id": item.id,
        "category": {
            "id": item.category_id,
            "name": item.category.name,
            "color": item.category.color,
            "kind": item.category.kind,
        },
        "period_start": item.period_start.isoformat(),
        "monthly_limit": _to_money(item.monthly_limit),
        "current_spending": _to_money(spent),
        "remaining_balance": _to_money(remaining),
        "progress_pct": utilization,
        "warning_threshold_pct": item.warning_threshold_pct,
        "is_active": item.is_active,
        "is_warning": utilization >= item.warning_threshold_pct,
        "is_over_limit": spent > item.monthly_limit,
    }


def _serialize_savings_goal(item, current_savings, suggestion):
    target = item.target_amount
    current = _safe_decimal(current_savings)
    progress = int((current / target) * 100) if target > 0 else 0
    progress = max(0, min(100, progress))
    return {
        "id": item.id,
        "name": item.name,
        "target_amount": _to_money(item.target_amount),
        "starting_amount": _to_money(item.starting_amount),
        "current_savings": _to_money(current),
        "progress_pct": progress,
        "deadline": item.deadline.isoformat() if item.deadline else None,
        "status": item.status,
        "monthly_target_suggestion": _to_money(suggestion),
    }


def _serialize_application_cost(item):
    return {
        "id": item.id,
        "item_type": item.item_type,
        "item_label": item.get_item_type_display(),
        "estimated_cost": _to_money(item.estimated_cost),
        "actual_cost": _to_money(item.actual_cost) if item.actual_cost is not None else None,
        "status": item.status,
        "deadline": item.deadline.isoformat() if item.deadline else None,
        "notes": item.notes,
    }


def _serialize_project_budget(item, spent_amount):
    spent = _safe_decimal(spent_amount)
    remaining = item.budget_amount - spent
    return {
        "id": item.id,
        "project_name": item.project_name,
        "budget_amount": _to_money(item.budget_amount),
        "spent_amount": _to_money(spent),
        "remaining_funds": _to_money(remaining),
        "roi_target_pct": float(item.roi_target_pct) if item.roi_target_pct is not None else None,
        "roi_actual_pct": float(item.roi_actual_pct) if item.roi_actual_pct is not None else None,
        "status": item.status,
    }


def _serialize_recurring(item):
    return {
        "id": item.id,
        "name": item.name,
        "category_id": item.category_id,
        "category_name": item.category.name,
        "account": item.account,
        "amount": _to_money(item.amount),
        "cadence": item.cadence,
        "next_due_date": item.next_due_date.isoformat(),
        "end_date": item.end_date.isoformat() if item.end_date else None,
        "is_active": item.is_active,
    }


def _serialize_alert(item):
    return {
        "id": item.id,
        "alert_type": item.alert_type,
        "severity": item.severity,
        "message": item.message,
        "related_model": item.related_model,
        "related_id": item.related_id,
        "period_key": item.period_key,
        "is_read": item.is_read,
        "created_at": item.created_at.isoformat(),
    }


def _compute_goal_suggestion(goal, current_savings, today):
    remaining = max(Decimal("0.00"), goal.target_amount - current_savings)
    if remaining <= 0:
        return Decimal("0.00")
    if goal.deadline is None:
        return remaining / Decimal("6.00")
    if goal.deadline <= today:
        return remaining

    month_diff = (goal.deadline.year - today.year) * 12 + (goal.deadline.month - today.month)
    if goal.deadline.day >= today.day:
        month_diff += 1
    month_diff = max(month_diff, 1)
    return remaining / Decimal(month_diff)


def _upsert_alert(alert_type, severity, message, related_model, related_id, period_key):
    alert, created = FinanceAlert.objects.get_or_create(
        alert_type=alert_type,
        related_model=related_model or "",
        related_id=related_id,
        period_key=period_key or "",
        defaults={"severity": severity, "message": message, "is_read": False},
    )
    if not created:
        changed = False
        if alert.severity != severity:
            alert.severity = severity
            changed = True
        if alert.message != message:
            alert.message = message
            changed = True
        if changed:
            alert.is_read = False
            alert.save(update_fields=["severity", "message", "is_read", "updated_at"])

def _filter_transactions(params):
    qs = Transaction.objects.select_related("category", "savings_goal", "application_cost", "project_budget")

    query = (params.get("q") or "").strip()
    if query:
        qs = qs.filter(description__icontains=query)

    date_from = _parse_date(params.get("date_from"))
    date_to = _parse_date(params.get("date_to"))
    if date_from:
        qs = qs.filter(tx_date__gte=date_from)
    if date_to:
        qs = qs.filter(tx_date__lte=date_to)

    category_id = (params.get("category_id") or "").strip()
    if category_id.isdigit():
        qs = qs.filter(category_id=int(category_id))

    account = (params.get("account") or "").strip()
    if account in {choice[0] for choice in Transaction.ACCOUNT_CHOICES}:
        qs = qs.filter(account=account)

    tx_type = (params.get("tx_type") or "").strip()
    if tx_type in {choice[0] for choice in Transaction.TYPE_CHOICES}:
        qs = qs.filter(tx_type=tx_type)

    amount_min = _safe_decimal(params.get("amount_min"), None)
    amount_max = _safe_decimal(params.get("amount_max"), None)
    if amount_min is not None:
        qs = qs.filter(amount__gte=amount_min)
    if amount_max is not None:
        qs = qs.filter(amount__lte=amount_max)

    sort_map = {
        "date_desc": "-tx_date",
        "date_asc": "tx_date",
        "amount_desc": "-amount",
        "amount_asc": "amount",
        "category_asc": "category__name",
        "category_desc": "-category__name",
        "updated_desc": "-updated_at",
    }
    sort = (params.get("sort") or "date_desc").strip()
    qs = qs.order_by(sort_map.get(sort, "-tx_date"), "-id")
    return qs


def _paginate_queryset(qs, params):
    page_size = params.get("page_size", 12)
    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        page_size = 12
    page_size = max(1, min(page_size, 100))

    page_number = params.get("page", 1)
    try:
        page_number = int(page_number)
    except (TypeError, ValueError):
        page_number = 1

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page_number)
    return page_obj, paginator


def _compute_finance_payload():
    today = date.today()
    current_start, current_end = _month_bounds(today)
    prev_start = _add_months(current_start, -1)
    prev_end = current_start

    current_qs = Transaction.objects.filter(tx_date__gte=current_start, tx_date__lt=current_end)
    prev_qs = Transaction.objects.filter(tx_date__gte=prev_start, tx_date__lt=prev_end)

    current_income = _safe_decimal(current_qs.filter(tx_type=Transaction.TYPE_INCOME).aggregate(total=Sum("amount"))["total"])
    current_expense = _safe_decimal(current_qs.filter(tx_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"])
    current_savings = _safe_decimal(current_qs.filter(tx_type=Transaction.TYPE_SAVINGS).aggregate(total=Sum("amount"))["total"])

    prev_income = _safe_decimal(prev_qs.filter(tx_type=Transaction.TYPE_INCOME).aggregate(total=Sum("amount"))["total"])
    prev_expense = _safe_decimal(prev_qs.filter(tx_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"])

    all_savings = _safe_decimal(Transaction.objects.filter(tx_type=Transaction.TYPE_SAVINGS).aggregate(total=Sum("amount"))["total"])
    app_estimated = _safe_decimal(ApplicationCost.objects.aggregate(total=Sum("estimated_cost"))["total"])
    app_actual = _safe_decimal(ApplicationCost.objects.exclude(actual_cost__isnull=True).aggregate(total=Sum("actual_cost"))["total"])

    budget_qs = Budget.objects.select_related("category").filter(period_start=current_start, is_active=True)
    budget_limit_total = _safe_decimal(budget_qs.aggregate(total=Sum("monthly_limit"))["total"])
    budget_spend_total = Decimal("0.00")
    for budget in budget_qs:
        spent = _safe_decimal(
            current_qs.filter(tx_type=Transaction.TYPE_EXPENSE, category=budget.category).aggregate(total=Sum("amount"))["total"]
        )
        budget_spend_total += spent

    monthly_budget_remaining = budget_limit_total - budget_spend_total
    cash_flow = current_income - current_expense

    investment_fund = _safe_decimal(
        Transaction.objects.filter(category__kind__in=[Category.KIND_INVESTMENT, Category.KIND_BUSINESS], tx_type=Transaction.TYPE_INCOME).aggregate(total=Sum("amount"))["total"]
    )
    scholarship_fund = max(Decimal("0.00"), app_estimated - app_actual)

    def pct_change(current, previous):
        if previous == 0:
            return 0
        return float(((current - previous) / previous) * Decimal("100.00"))

    metrics = [
        {
            "key": "monthly_income",
            "label": "Monthly Income",
            "icon": "fa-sack-dollar",
            "value": _to_money(current_income),
            "trend": pct_change(current_income, prev_income),
            "description": "Total income for the current month.",
        },
        {
            "key": "total_expenses",
            "label": "Total Expenses",
            "icon": "fa-arrow-trend-down",
            "value": _to_money(current_expense),
            "trend": pct_change(current_expense, prev_expense),
            "description": "Total spending for the current month.",
        },
        {
            "key": "net_savings",
            "label": "Net Savings",
            "icon": "fa-piggy-bank",
            "value": _to_money(current_income - current_expense),
            "trend": pct_change(current_income - current_expense, prev_income - prev_expense),
            "description": "Income minus expenses in the current month.",
        },
        {
            "key": "application_budget",
            "label": "Application Budget",
            "icon": "fa-graduation-cap",
            "value": _to_money(app_estimated),
            "trend": 0,
            "description": "Total planned scholarship/application spending.",
        },
        {
            "key": "cash_flow",
            "label": "Cash Flow",
            "icon": "fa-arrows-left-right",
            "value": _to_money(cash_flow),
            "trend": pct_change(cash_flow, prev_income - prev_expense),
            "description": "Money movement after costs this month.",
        },
        {
            "key": "budget_remaining",
            "label": "Monthly Budget Remaining",
            "icon": "fa-scale-balanced",
            "value": _to_money(monthly_budget_remaining),
            "trend": 0,
            "description": "Configured monthly budgets minus tracked spending.",
        },
        {
            "key": "total_savings_balance",
            "label": "Total Savings Balance",
            "icon": "fa-vault",
            "value": _to_money(all_savings),
            "trend": 0,
            "description": "Cumulative savings transactions recorded.",
        },
        {
            "key": "scholarship_fund",
            "label": "Scholarship Application Fund",
            "icon": "fa-passport",
            "value": _to_money(scholarship_fund),
            "trend": 0,
            "description": "Estimated application costs still outstanding.",
        },
        {
            "key": "investment_fund",
            "label": "Investment / Business Fund",
            "icon": "fa-chart-line",
            "value": _to_money(investment_fund),
            "trend": 0,
            "description": "Capital allocated to projects and investments.",
        },
    ]

    # Budgets
    budget_items = []
    budget_overrun_count = 0
    budget_warning_count = 0
    for budget in budget_qs:
        spent = _safe_decimal(
            current_qs.filter(tx_type=Transaction.TYPE_EXPENSE, category=budget.category).aggregate(total=Sum("amount"))["total"]
        )
        payload = _serialize_budget(budget, spent)
        budget_items.append(payload)
        if payload["is_over_limit"]:
            budget_overrun_count += 1
        elif payload["is_warning"]:
            budget_warning_count += 1

    # Savings goals
    goals_payload = []
    goals_at_risk = 0
    for goal in SavingsGoal.objects.all():
        goal_saved = _safe_decimal(
            Transaction.objects.filter(tx_type=Transaction.TYPE_SAVINGS, savings_goal=goal).aggregate(total=Sum("amount"))["total"]
        )
        current_saved = goal.starting_amount + goal_saved
        suggestion = _compute_goal_suggestion(goal, current_saved, today)
        goals_payload.append(_serialize_savings_goal(goal, current_saved, suggestion))

        if goal.deadline and goal.deadline > today and current_saved < goal.target_amount:
            if suggestion > Decimal("0") and suggestion > (goal.target_amount * Decimal("0.20")):
                goals_at_risk += 1

    # Application costs
    application_items = [_serialize_application_cost(item) for item in ApplicationCost.objects.all()]

    # Project budgets
    project_payload = []
    for project in ProjectBudget.objects.all():
        project_spent = _safe_decimal(project.manual_spent_adjustment)
        project_spent += _safe_decimal(
            Transaction.objects.filter(project_budget=project, tx_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"]
        )
        project_payload.append(_serialize_project_budget(project, project_spent))

    # Recurring forecast preview 60 days
    recurring_preview = _compute_forecast(days=60)

    # Alerts (hybrid persisted)
    period_key = _month_key(today)
    for budget_item in budget_items:
        if budget_item["is_over_limit"]:
            _upsert_alert(
                FinanceAlert.TYPE_BUDGET_OVERRUN,
                FinanceAlert.SEVERITY_CRITICAL,
                f"{budget_item['category']['name']} is over budget by KES {abs(budget_item['remaining_balance']):,.2f}.",
                "budget",
                budget_item["id"],
                period_key,
            )
        elif budget_item["is_warning"]:
            _upsert_alert(
                FinanceAlert.TYPE_BUDGET_OVERRUN,
                FinanceAlert.SEVERITY_WARNING,
                f"{budget_item['category']['name']} has reached {budget_item['progress_pct']}% of monthly limit.",
                "budget",
                budget_item["id"],
                period_key,
            )

    if cash_flow < 0:
        _upsert_alert(
            FinanceAlert.TYPE_CASHFLOW,
            FinanceAlert.SEVERITY_WARNING,
            "Cash flow is negative this month. Reduce expenses or increase income sources.",
            "system",
            1,
            period_key,
        )

    for app in ApplicationCost.objects.exclude(status__in=[ApplicationCost.STATUS_PAID, ApplicationCost.STATUS_WAIVED, ApplicationCost.STATUS_CANCELLED]):
        if app.deadline and 0 <= (app.deadline - today).days <= 21:
            _upsert_alert(
                FinanceAlert.TYPE_DEADLINE,
                FinanceAlert.SEVERITY_WARNING,
                f"{app.get_item_type_display()} deadline is in {(app.deadline - today).days} days.",
                "application_cost",
                app.id,
                _month_key(app.deadline),
            )

    if goals_at_risk > 0:
        _upsert_alert(
            FinanceAlert.TYPE_GOAL_RISK,
            FinanceAlert.SEVERITY_WARNING,
            f"{goals_at_risk} savings goal(s) are at risk of missing target deadlines.",
            "savings_goal",
            None,
            period_key,
        )

    alerts_payload = [_serialize_alert(item) for item in FinanceAlert.objects.all()[:50]]

    # Insights (computed on-demand)
    insights = []
    food_like = Category.objects.filter(name__icontains="living").values_list("id", flat=True)
    current_food = _safe_decimal(current_qs.filter(category_id__in=food_like, tx_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"])
    prev_food = _safe_decimal(prev_qs.filter(category_id__in=food_like, tx_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"])
    if prev_food > 0:
        diff = ((current_food - prev_food) / prev_food) * Decimal("100.00")
        if diff > 15:
            insights.append({"tag": "Budget", "message": f"Living costs increased {float(diff):.1f}% compared to last month."})

    if current_savings > 0 and current_income > 0:
        save_rate = (current_savings / current_income) * Decimal("100.00")
        insights.append({"tag": "Savings", "message": f"You are saving {float(save_rate):.1f}% of monthly income."})

    if scholarship_fund > 0:
        insights.append({"tag": "Scholarships", "message": f"KES {float(scholarship_fund):,.0f} still needed for application pipeline."})

    # Charts
    month_labels = []
    income_series = []
    expense_series = []
    savings_series = []
    balance_series = []
    running_balance = Decimal("0.00")
    for idx in range(5, -1, -1):
        start = _add_months(current_start, -idx)
        end = _add_months(start, 1)
        label = start.strftime("%b")
        month_labels.append(label)
        month_qs = Transaction.objects.filter(tx_date__gte=start, tx_date__lt=end)
        income_v = _safe_decimal(month_qs.filter(tx_type=Transaction.TYPE_INCOME).aggregate(total=Sum("amount"))["total"])
        expense_v = _safe_decimal(month_qs.filter(tx_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"])
        savings_v = _safe_decimal(month_qs.filter(tx_type=Transaction.TYPE_SAVINGS).aggregate(total=Sum("amount"))["total"])
        running_balance += income_v - expense_v
        income_series.append(_to_money(income_v))
        expense_series.append(_to_money(expense_v))
        savings_series.append(_to_money(savings_v))
        balance_series.append(_to_money(running_balance))

    category_breakdown = []
    for category in Category.objects.filter(is_active=True):
        value = _safe_decimal(current_qs.filter(category=category, tx_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"])
        if value > 0:
            category_breakdown.append(
                {
                    "label": category.name,
                    "value": _to_money(value),
                    "color": category.color,
                }
            )

    budget_util = [
        {
            "label": item["category"]["name"],
            "value": item["progress_pct"],
            "color": item["category"]["color"],
        }
        for item in budget_items
    ]

    app_breakdown = [
        {
            "label": item["item_label"],
            "estimated": item["estimated_cost"],
            "actual": item["actual_cost"] or 0,
        }
        for item in application_items
    ]

    project_roi = [
        {
            "label": item["project_name"],
            "target": item["roi_target_pct"] or 0,
            "actual": item["roi_actual_pct"] or 0,
        }
        for item in project_payload
    ]

    return {
        "metrics": metrics,
        "budgets": budget_items,
        "savings_goals": goals_payload,
        "application_costs": application_items,
        "project_budgets": project_payload,
        "recurring_forecast": recurring_preview,
        "alerts": alerts_payload,
        "insights": insights,
        "summary": {
            "cash_flow": _to_money(cash_flow),
            "budget_remaining": _to_money(monthly_budget_remaining),
            "total_savings": _to_money(all_savings),
            "application_estimated_total": _to_money(app_estimated),
            "application_actual_total": _to_money(app_actual),
            "budget_warning_count": budget_warning_count,
            "budget_overrun_count": budget_overrun_count,
        },
        "charts": {
            "monthly_income_vs_expenses": {
                "labels": month_labels,
                "income": income_series,
                "expenses": expense_series,
            },
            "expense_category_distribution": category_breakdown,
            "savings_growth": {
                "labels": month_labels,
                "values": savings_series,
            },
            "budget_utilization": budget_util,
            "application_cost_breakdown": app_breakdown,
            "project_roi": project_roi,
            "cash_balance_trend": {
                "labels": month_labels,
                "values": balance_series,
            },
        },
    }


def _compute_forecast(days=30):
    horizon = date.today() + timedelta(days=days)
    forecast_rows = []
    for template in RecurringExpenseTemplate.objects.select_related("category").filter(is_active=True):
        due = template.next_due_date
        while due <= horizon:
            if template.end_date and due > template.end_date:
                break
            forecast_rows.append(
                {
                    "template_id": template.id,
                    "template_name": template.name,
                    "category": template.category.name,
                    "category_color": template.category.color,
                    "amount": _to_money(template.amount),
                    "account": template.account,
                    "due_date": due.isoformat(),
                }
            )
            if template.cadence == RecurringExpenseTemplate.CADENCE_WEEKLY:
                due = due + timedelta(days=7)
            elif template.cadence == RecurringExpenseTemplate.CADENCE_YEARLY:
                due = _add_months(due, 12)
            else:
                due = _add_months(due, 1)

    forecast_rows.sort(key=lambda row: row["due_date"])
    return forecast_rows[:200]


@require_GET
def finance_bootstrap(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    base_payload = _compute_finance_payload()
    transaction_qs = _filter_transactions(request.GET)
    page_obj, paginator = _paginate_queryset(transaction_qs, request.GET)
    ledger = [_serialize_transaction(item) for item in page_obj.object_list]

    payload = {
        "ok": True,
        **base_payload,
        "ledger": {
            "rows": ledger,
            "pagination": {
                "page": page_obj.number,
                "page_size": page_obj.paginator.per_page,
                "total_pages": paginator.num_pages,
                "total_items": paginator.count,
                "has_next": page_obj.has_next(),
                "has_prev": page_obj.has_previous(),
            },
        },
    }
    return JsonResponse(payload)


@require_GET
def finance_transactions(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    qs = _filter_transactions(request.GET)
    page_obj, paginator = _paginate_queryset(qs, request.GET)
    rows = [_serialize_transaction(item) for item in page_obj.object_list]
    return JsonResponse(
        {
            "ok": True,
            "rows": rows,
            "pagination": {
                "page": page_obj.number,
                "page_size": page_obj.paginator.per_page,
                "total_pages": paginator.num_pages,
                "total_items": paginator.count,
                "has_next": page_obj.has_next(),
                "has_prev": page_obj.has_previous(),
            },
        }
    )


@require_POST
def finance_transactions_create(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    payload = _parse_json(request)
    tx_date = _parse_date(payload.get("tx_date"))
    if not tx_date:
        return _json_error("Valid transaction date is required")

    description = (payload.get("description") or "").strip()
    if not description:
        return _json_error("Description is required")

    category_id = payload.get("category_id")
    category = Category.objects.filter(id=category_id).first()
    if not category:
        return _json_error("Valid category is required")

    account = (payload.get("account") or Transaction.ACCOUNT_BANK).strip()
    if account not in {choice[0] for choice in Transaction.ACCOUNT_CHOICES}:
        return _json_error("Invalid account")

    tx_type = (payload.get("tx_type") or Transaction.TYPE_EXPENSE).strip()
    if tx_type not in {choice[0] for choice in Transaction.TYPE_CHOICES}:
        return _json_error("Invalid transaction type")

    amount = _safe_decimal(payload.get("amount"), None)
    if amount is None or amount <= 0:
        return _json_error("Amount must be greater than zero")

    tags = _split_tags(payload.get("tags"))

    savings_goal = None
    if payload.get("savings_goal_id"):
        savings_goal = SavingsGoal.objects.filter(id=payload.get("savings_goal_id")).first()

    application_cost = None
    if payload.get("application_cost_id"):
        application_cost = ApplicationCost.objects.filter(id=payload.get("application_cost_id")).first()

    project_budget = None
    if payload.get("project_budget_id"):
        project_budget = ProjectBudget.objects.filter(id=payload.get("project_budget_id")).first()

    tx = Transaction.objects.create(
        tx_date=tx_date,
        description=description,
        category=category,
        account=account,
        tx_type=tx_type,
        amount=amount,
        tags=tags,
        savings_goal=savings_goal,
        application_cost=application_cost,
        project_budget=project_budget,
        notes=(payload.get("notes") or "").strip(),
    )
    return JsonResponse({"ok": True, "transaction": _serialize_transaction(tx)}, status=201)


@require_POST
def finance_transactions_update(request, transaction_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    tx = get_object_or_404(Transaction, id=transaction_id)
    payload = _parse_json(request)

    tx_date = _parse_date(payload.get("tx_date"))
    if not tx_date:
        return _json_error("Valid transaction date is required")

    description = (payload.get("description") or "").strip()
    if not description:
        return _json_error("Description is required")

    category = Category.objects.filter(id=payload.get("category_id")).first()
    if not category:
        return _json_error("Valid category is required")

    account = (payload.get("account") or Transaction.ACCOUNT_BANK).strip()
    if account not in {choice[0] for choice in Transaction.ACCOUNT_CHOICES}:
        return _json_error("Invalid account")

    tx_type = (payload.get("tx_type") or Transaction.TYPE_EXPENSE).strip()
    if tx_type not in {choice[0] for choice in Transaction.TYPE_CHOICES}:
        return _json_error("Invalid transaction type")

    amount = _safe_decimal(payload.get("amount"), None)
    if amount is None or amount <= 0:
        return _json_error("Amount must be greater than zero")

    tx.tx_date = tx_date
    tx.description = description
    tx.category = category
    tx.account = account
    tx.tx_type = tx_type
    tx.amount = amount
    tx.tags = _split_tags(payload.get("tags"))
    tx.notes = (payload.get("notes") or "").strip()
    tx.savings_goal = SavingsGoal.objects.filter(id=payload.get("savings_goal_id")).first() if payload.get("savings_goal_id") else None
    tx.application_cost = ApplicationCost.objects.filter(id=payload.get("application_cost_id")).first() if payload.get("application_cost_id") else None
    tx.project_budget = ProjectBudget.objects.filter(id=payload.get("project_budget_id")).first() if payload.get("project_budget_id") else None
    tx.save()
    return JsonResponse({"ok": True, "transaction": _serialize_transaction(tx)})


@require_POST
def finance_transactions_delete(request, transaction_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    tx = get_object_or_404(Transaction, id=transaction_id)
    tx.delete()
    return JsonResponse({"ok": True})


@require_GET
def finance_transactions_export_csv(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    qs = _filter_transactions(request.GET)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="finance-transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(["Date", "Description", "Category", "Account", "Type", "Amount", "Tags", "Notes"])
    for item in qs[:5000]:
        writer.writerow(
            [
                item.tx_date.isoformat(),
                item.description,
                item.category.name,
                item.account,
                item.tx_type,
                str(item.amount),
                ", ".join(item.tags or []),
                item.notes,
            ]
        )

    return response


@require_GET
def finance_categories(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    rows = [_serialize_category(cat) for cat in Category.objects.all()]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def finance_categories_create(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)

    name = (payload.get("name") or "").strip()
    if not name:
        return _json_error("Category name is required")

    kind = (payload.get("kind") or Category.KIND_EXPENSE).strip()
    if kind not in {choice[0] for choice in Category.KIND_CHOICES}:
        return _json_error("Invalid category kind")

    slug = (payload.get("slug") or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")).strip()
    if not slug:
        return _json_error("Valid category slug is required")
    if Category.objects.filter(slug=slug).exists():
        return _json_error("Category slug already exists")

    category = Category.objects.create(
        name=name,
        slug=slug,
        kind=kind,
        color=(payload.get("color") or "#8B5A2B").strip()[:16],
        icon=(payload.get("icon") or "fa-wallet").strip()[:40],
        is_active=bool(payload.get("is_active", True)),
        sort_order=int(payload.get("sort_order") or 0),
    )
    return JsonResponse({"ok": True, "category": _serialize_category(category)}, status=201)


@require_POST
def finance_categories_update(request, category_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    category = get_object_or_404(Category, id=category_id)
    payload = _parse_json(request)

    name = (payload.get("name") or category.name).strip()
    slug = (payload.get("slug") or category.slug).strip()
    kind = (payload.get("kind") or category.kind).strip()

    if kind not in {choice[0] for choice in Category.KIND_CHOICES}:
        return _json_error("Invalid category kind")
    if Category.objects.exclude(id=category.id).filter(slug=slug).exists():
        return _json_error("Category slug already exists")

    category.name = name
    category.slug = slug
    category.kind = kind
    category.color = (payload.get("color") or category.color).strip()[:16]
    category.icon = (payload.get("icon") or category.icon).strip()[:40]
    category.is_active = bool(payload.get("is_active", category.is_active))
    category.sort_order = int(payload.get("sort_order") if payload.get("sort_order") is not None else category.sort_order)
    category.save()
    return JsonResponse({"ok": True, "category": _serialize_category(category)})


@require_POST
def finance_categories_delete(request, category_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    category = get_object_or_404(Category, id=category_id)
    if Transaction.objects.filter(category=category).exists():
        return _json_error("Cannot delete category with existing transactions", status=409)
    if Budget.objects.filter(category=category).exists():
        return _json_error("Cannot delete category with existing budgets", status=409)
    if RecurringExpenseTemplate.objects.filter(category=category).exists():
        return _json_error("Cannot delete category with recurring templates", status=409)
    category.delete()
    return JsonResponse({"ok": True})


@require_GET
def finance_budgets(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    rows = []
    for item in Budget.objects.select_related("category").all():
        month_start, month_end = _month_bounds(item.period_start)
        spent = _safe_decimal(
            Transaction.objects.filter(
                tx_type=Transaction.TYPE_EXPENSE,
                category=item.category,
                tx_date__gte=month_start,
                tx_date__lt=month_end,
            ).aggregate(total=Sum("amount"))["total"]
        )
        rows.append(_serialize_budget(item, spent))
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def finance_budgets_create(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    payload = _parse_json(request)
    category = Category.objects.filter(id=payload.get("category_id")).first()
    if not category:
        return _json_error("Valid category is required")

    period_start = _parse_date(payload.get("period_start"))
    if not period_start:
        return _json_error("Valid period start date is required")
    period_start = _month_start(period_start)

    monthly_limit = _safe_decimal(payload.get("monthly_limit"), None)
    if monthly_limit is None or monthly_limit <= 0:
        return _json_error("Monthly limit must be greater than zero")

    if Budget.objects.filter(category=category, period_start=period_start).exists():
        return _json_error("Budget for this category and month already exists", status=409)

    item = Budget.objects.create(
        category=category,
        period_start=period_start,
        monthly_limit=monthly_limit,
        warning_threshold_pct=int(payload.get("warning_threshold_pct") or 90),
        is_active=bool(payload.get("is_active", True)),
    )
    return JsonResponse({"ok": True, "budget": _serialize_budget(item, Decimal("0.00"))}, status=201)


@require_POST
def finance_budgets_update(request, budget_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    item = get_object_or_404(Budget, id=budget_id)
    payload = _parse_json(request)

    category = Category.objects.filter(id=payload.get("category_id")).first() if payload.get("category_id") else item.category
    period_start = _parse_date(payload.get("period_start")) if payload.get("period_start") else item.period_start
    period_start = _month_start(period_start)

    monthly_limit = _safe_decimal(payload.get("monthly_limit"), item.monthly_limit)
    if monthly_limit <= 0:
        return _json_error("Monthly limit must be greater than zero")

    if Budget.objects.exclude(id=item.id).filter(category=category, period_start=period_start).exists():
        return _json_error("Budget for this category and month already exists", status=409)

    item.category = category
    item.period_start = period_start
    item.monthly_limit = monthly_limit
    item.warning_threshold_pct = int(payload.get("warning_threshold_pct") or item.warning_threshold_pct)
    item.is_active = bool(payload.get("is_active", item.is_active))
    item.save()

    spent = _safe_decimal(
        Transaction.objects.filter(
            tx_type=Transaction.TYPE_EXPENSE,
            category=item.category,
            tx_date__gte=period_start,
            tx_date__lt=_add_months(period_start, 1),
        ).aggregate(total=Sum("amount"))["total"]
    )
    return JsonResponse({"ok": True, "budget": _serialize_budget(item, spent)})


@require_POST
def finance_budgets_delete(request, budget_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(Budget, id=budget_id)
    item.delete()
    return JsonResponse({"ok": True})


@require_GET
def finance_savings_goals(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    today = date.today()
    rows = []
    for goal in SavingsGoal.objects.all():
        tracked = _safe_decimal(Transaction.objects.filter(tx_type=Transaction.TYPE_SAVINGS, savings_goal=goal).aggregate(total=Sum("amount"))["total"])
        current = goal.starting_amount + tracked
        suggestion = _compute_goal_suggestion(goal, current, today)
        rows.append(_serialize_savings_goal(goal, current, suggestion))
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def finance_savings_goals_create(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    payload = _parse_json(request)
    name = (payload.get("name") or "").strip()
    if not name:
        return _json_error("Goal name is required")

    target_amount = _safe_decimal(payload.get("target_amount"), None)
    if target_amount is None or target_amount <= 0:
        return _json_error("Target amount must be greater than zero")

    starting_amount = _safe_decimal(payload.get("starting_amount"), Decimal("0.00"))
    deadline = _parse_date(payload.get("deadline"))
    status = (payload.get("status") or SavingsGoal.STATUS_ACTIVE).strip()
    if status not in {choice[0] for choice in SavingsGoal.STATUS_CHOICES}:
        return _json_error("Invalid status")

    goal = SavingsGoal.objects.create(
        name=name,
        target_amount=target_amount,
        starting_amount=max(Decimal("0.00"), starting_amount),
        deadline=deadline,
        status=status,
        monthly_target_suggestion=_safe_decimal(payload.get("monthly_target_suggestion"), Decimal("0.00")),
    )
    suggestion = _compute_goal_suggestion(goal, goal.starting_amount, date.today())
    return JsonResponse({"ok": True, "goal": _serialize_savings_goal(goal, goal.starting_amount, suggestion)}, status=201)


@require_POST
def finance_savings_goals_update(request, goal_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    goal = get_object_or_404(SavingsGoal, id=goal_id)
    payload = _parse_json(request)

    name = (payload.get("name") or goal.name).strip()
    target_amount = _safe_decimal(payload.get("target_amount"), goal.target_amount)
    if target_amount <= 0:
        return _json_error("Target amount must be greater than zero")

    goal.name = name
    goal.target_amount = target_amount
    goal.starting_amount = max(Decimal("0.00"), _safe_decimal(payload.get("starting_amount"), goal.starting_amount))
    goal.deadline = _parse_date(payload.get("deadline")) if payload.get("deadline") is not None else goal.deadline
    status = (payload.get("status") or goal.status).strip()
    if status not in {choice[0] for choice in SavingsGoal.STATUS_CHOICES}:
        return _json_error("Invalid status")
    goal.status = status
    goal.monthly_target_suggestion = _safe_decimal(payload.get("monthly_target_suggestion"), goal.monthly_target_suggestion)
    goal.save()

    tracked = _safe_decimal(Transaction.objects.filter(tx_type=Transaction.TYPE_SAVINGS, savings_goal=goal).aggregate(total=Sum("amount"))["total"])
    current = goal.starting_amount + tracked
    suggestion = _compute_goal_suggestion(goal, current, date.today())
    return JsonResponse({"ok": True, "goal": _serialize_savings_goal(goal, current, suggestion)})


@require_POST
def finance_savings_goals_delete(request, goal_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    goal = get_object_or_404(SavingsGoal, id=goal_id)
    Transaction.objects.filter(savings_goal=goal).update(savings_goal=None)
    goal.delete()
    return JsonResponse({"ok": True})


@require_GET
def finance_application_costs(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    rows = [_serialize_application_cost(item) for item in ApplicationCost.objects.all()]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def finance_application_costs_create(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)

    item_type = (payload.get("item_type") or ApplicationCost.TYPE_OTHER).strip()
    if item_type not in {choice[0] for choice in ApplicationCost.ITEM_TYPE_CHOICES}:
        return _json_error("Invalid item type")

    estimated_cost = _safe_decimal(payload.get("estimated_cost"), None)
    if estimated_cost is None or estimated_cost < 0:
        return _json_error("Estimated cost must be zero or greater")

    status = (payload.get("status") or ApplicationCost.STATUS_PLANNED).strip()
    if status not in {choice[0] for choice in ApplicationCost.STATUS_CHOICES}:
        return _json_error("Invalid status")

    item = ApplicationCost.objects.create(
        item_type=item_type,
        estimated_cost=estimated_cost,
        actual_cost=_safe_decimal(payload.get("actual_cost"), None) if payload.get("actual_cost") not in (None, "") else None,
        status=status,
        deadline=_parse_date(payload.get("deadline")),
        notes=(payload.get("notes") or "").strip(),
    )
    return JsonResponse({"ok": True, "application_cost": _serialize_application_cost(item)}, status=201)


@require_POST
def finance_application_costs_update(request, cost_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ApplicationCost, id=cost_id)
    payload = _parse_json(request)

    item_type = (payload.get("item_type") or item.item_type).strip()
    if item_type not in {choice[0] for choice in ApplicationCost.ITEM_TYPE_CHOICES}:
        return _json_error("Invalid item type")

    status = (payload.get("status") or item.status).strip()
    if status not in {choice[0] for choice in ApplicationCost.STATUS_CHOICES}:
        return _json_error("Invalid status")

    estimated_cost = _safe_decimal(payload.get("estimated_cost"), item.estimated_cost)
    if estimated_cost < 0:
        return _json_error("Estimated cost must be zero or greater")

    item.item_type = item_type
    item.estimated_cost = estimated_cost
    item.actual_cost = _safe_decimal(payload.get("actual_cost"), None) if payload.get("actual_cost") not in (None, "") else None
    item.status = status
    item.deadline = _parse_date(payload.get("deadline")) if payload.get("deadline") is not None else item.deadline
    item.notes = (payload.get("notes") or item.notes).strip()
    item.save()

    return JsonResponse({"ok": True, "application_cost": _serialize_application_cost(item)})


@require_POST
def finance_application_costs_delete(request, cost_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ApplicationCost, id=cost_id)
    Transaction.objects.filter(application_cost=item).update(application_cost=None)
    item.delete()
    return JsonResponse({"ok": True})


@require_GET
def finance_project_budgets(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    rows = []
    for item in ProjectBudget.objects.all():
        spent = _safe_decimal(item.manual_spent_adjustment)
        spent += _safe_decimal(Transaction.objects.filter(project_budget=item, tx_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"])
        rows.append(_serialize_project_budget(item, spent))
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def finance_project_budgets_create(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)

    name = (payload.get("project_name") or "").strip()
    if not name:
        return _json_error("Project name is required")

    budget_amount = _safe_decimal(payload.get("budget_amount"), None)
    if budget_amount is None or budget_amount <= 0:
        return _json_error("Budget amount must be greater than zero")

    status = (payload.get("status") or ProjectBudget.STATUS_ACTIVE).strip()
    if status not in {choice[0] for choice in ProjectBudget.STATUS_CHOICES}:
        return _json_error("Invalid status")

    item = ProjectBudget.objects.create(
        project_name=name,
        budget_amount=budget_amount,
        manual_spent_adjustment=max(Decimal("0.00"), _safe_decimal(payload.get("manual_spent_adjustment"), Decimal("0.00"))),
        roi_target_pct=_safe_decimal(payload.get("roi_target_pct"), None) if payload.get("roi_target_pct") not in (None, "") else None,
        roi_actual_pct=_safe_decimal(payload.get("roi_actual_pct"), None) if payload.get("roi_actual_pct") not in (None, "") else None,
        status=status,
    )
    spent = _safe_decimal(item.manual_spent_adjustment)
    return JsonResponse({"ok": True, "project_budget": _serialize_project_budget(item, spent)}, status=201)


@require_POST
def finance_project_budgets_update(request, project_budget_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ProjectBudget, id=project_budget_id)
    payload = _parse_json(request)

    item.project_name = (payload.get("project_name") or item.project_name).strip()
    budget_amount = _safe_decimal(payload.get("budget_amount"), item.budget_amount)
    if budget_amount <= 0:
        return _json_error("Budget amount must be greater than zero")
    item.budget_amount = budget_amount
    item.manual_spent_adjustment = max(Decimal("0.00"), _safe_decimal(payload.get("manual_spent_adjustment"), item.manual_spent_adjustment))

    status = (payload.get("status") or item.status).strip()
    if status not in {choice[0] for choice in ProjectBudget.STATUS_CHOICES}:
        return _json_error("Invalid status")
    item.status = status

    item.roi_target_pct = _safe_decimal(payload.get("roi_target_pct"), None) if payload.get("roi_target_pct") not in (None, "") else None
    item.roi_actual_pct = _safe_decimal(payload.get("roi_actual_pct"), None) if payload.get("roi_actual_pct") not in (None, "") else None
    item.save()

    spent = _safe_decimal(item.manual_spent_adjustment)
    spent += _safe_decimal(Transaction.objects.filter(project_budget=item, tx_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum("amount"))["total"])
    return JsonResponse({"ok": True, "project_budget": _serialize_project_budget(item, spent)})


@require_POST
def finance_project_budgets_delete(request, project_budget_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ProjectBudget, id=project_budget_id)
    Transaction.objects.filter(project_budget=item).update(project_budget=None)
    item.delete()
    return JsonResponse({"ok": True})


@require_GET
def finance_recurring(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    rows = [_serialize_recurring(item) for item in RecurringExpenseTemplate.objects.select_related("category").all()]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def finance_recurring_create(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)

    name = (payload.get("name") or "").strip()
    if not name:
        return _json_error("Recurring template name is required")

    category = Category.objects.filter(id=payload.get("category_id")).first()
    if not category:
        return _json_error("Valid category is required")

    amount = _safe_decimal(payload.get("amount"), None)
    if amount is None or amount <= 0:
        return _json_error("Amount must be greater than zero")

    account = (payload.get("account") or Transaction.ACCOUNT_BANK).strip()
    if account not in {choice[0] for choice in Transaction.ACCOUNT_CHOICES}:
        return _json_error("Invalid account")

    cadence = (payload.get("cadence") or RecurringExpenseTemplate.CADENCE_MONTHLY).strip()
    if cadence not in {choice[0] for choice in RecurringExpenseTemplate.CADENCE_CHOICES}:
        return _json_error("Invalid cadence")

    next_due_date = _parse_date(payload.get("next_due_date"))
    if not next_due_date:
        return _json_error("Valid next due date is required")

    item = RecurringExpenseTemplate.objects.create(
        name=name,
        category=category,
        account=account,
        amount=amount,
        cadence=cadence,
        next_due_date=next_due_date,
        end_date=_parse_date(payload.get("end_date")),
        is_active=bool(payload.get("is_active", True)),
    )
    return JsonResponse({"ok": True, "recurring": _serialize_recurring(item)}, status=201)


@require_POST
def finance_recurring_update(request, recurring_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(RecurringExpenseTemplate, id=recurring_id)
    payload = _parse_json(request)

    item.name = (payload.get("name") or item.name).strip()
    category = Category.objects.filter(id=payload.get("category_id")).first() if payload.get("category_id") else item.category
    item.category = category

    amount = _safe_decimal(payload.get("amount"), item.amount)
    if amount <= 0:
        return _json_error("Amount must be greater than zero")
    item.amount = amount

    account = (payload.get("account") or item.account).strip()
    if account not in {choice[0] for choice in Transaction.ACCOUNT_CHOICES}:
        return _json_error("Invalid account")
    item.account = account

    cadence = (payload.get("cadence") or item.cadence).strip()
    if cadence not in {choice[0] for choice in RecurringExpenseTemplate.CADENCE_CHOICES}:
        return _json_error("Invalid cadence")
    item.cadence = cadence

    next_due_date = _parse_date(payload.get("next_due_date")) if payload.get("next_due_date") else item.next_due_date
    if not next_due_date:
        return _json_error("Valid next due date is required")
    item.next_due_date = next_due_date

    item.end_date = _parse_date(payload.get("end_date")) if payload.get("end_date") is not None else item.end_date
    item.is_active = bool(payload.get("is_active", item.is_active))
    item.save()

    return JsonResponse({"ok": True, "recurring": _serialize_recurring(item)})


@require_POST
def finance_recurring_delete(request, recurring_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(RecurringExpenseTemplate, id=recurring_id)
    item.delete()
    return JsonResponse({"ok": True})


@require_GET
def finance_forecast(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    days = request.GET.get("days", 30)
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 30
    days = 30 if days not in {30, 60} else days
    return JsonResponse({"ok": True, "rows": _compute_forecast(days=days)})


@require_POST
def finance_recurring_apply_now(request, recurring_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error

    template = get_object_or_404(RecurringExpenseTemplate.objects.select_related("category"), id=recurring_id)
    tx = Transaction.objects.create(
        tx_date=date.today(),
        description=f"Recurring: {template.name}",
        category=template.category,
        account=template.account,
        tx_type=Transaction.TYPE_EXPENSE,
        amount=template.amount,
        tags=["recurring", template.cadence],
        notes="Generated from recurring template",
    )

    if template.cadence == RecurringExpenseTemplate.CADENCE_WEEKLY:
        template.next_due_date = template.next_due_date + timedelta(days=7)
    elif template.cadence == RecurringExpenseTemplate.CADENCE_YEARLY:
        template.next_due_date = _add_months(template.next_due_date, 12)
    else:
        template.next_due_date = _add_months(template.next_due_date, 1)
    template.save(update_fields=["next_due_date", "updated_at"])

    return JsonResponse({"ok": True, "transaction": _serialize_transaction(tx)})


@require_GET
def finance_alerts(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    rows = [_serialize_alert(item) for item in FinanceAlert.objects.all()[:200]]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def finance_alert_mark_read(request, alert_id):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(FinanceAlert, id=alert_id)
    item.is_read = True
    item.save(update_fields=["is_read", "updated_at"])
    return JsonResponse({"ok": True})


@require_POST
def finance_alert_mark_all_read(request):
    auth_error = _require_finance_access(request)
    if auth_error:
        return auth_error
    FinanceAlert.objects.filter(is_read=False).update(is_read=True)
    return JsonResponse({"ok": True})


# -----------------------------
# Education command center APIs
# -----------------------------


def _parse_request_data(request):
    if request.content_type and "application/json" in request.content_type:
        return _parse_json(request)
    return request.POST.dict()


def _bool_value(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return default


def _optional_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _serialize_exam(exam):
    return {
        "id": exam.id,
        "academic_level_id": exam.academic_level_id,
        "exam_name": exam.exam_name,
        "exam_year": exam.exam_year,
        "candidate_number": exam.candidate_number,
        "grade_score": exam.grade_score,
        "certificate_url": exam.certificate_file.url if exam.certificate_file else "",
        "notes": exam.notes,
        "updated_at": exam.updated_at.isoformat(),
    }


def _serialize_academic_level(level):
    return {
        "id": level.id,
        "level_type": level.level_type,
        "level_label": level.get_level_type_display(),
        "status": level.status,
        "school_name": level.school_name,
        "admission_number": level.admission_number,
        "location": level.location,
        "start_year": level.start_year,
        "end_year": level.end_year,
        "subjects_taken": level.subjects_taken,
        "grades": level.grades,
        "certification_exam_completed": level.certification_exam_completed,
        "certificate_url": level.certificate_file.url if level.certificate_file else "",
        "university_name": level.university_name,
        "country": level.country,
        "degree": level.degree,
        "major_program": level.major_program,
        "expected_graduation_year": level.expected_graduation_year,
        "student_number": level.student_number,
        "gpa": level.gpa,
        "transcript_url": level.transcript_file.url if level.transcript_file else "",
        "research_topic": level.research_topic,
        "internships": level.internships,
        "clubs_activities": level.clubs_activities,
        "awards": level.awards,
        "notes": level.notes,
        "exam_certifications": [_serialize_exam(exam) for exam in level.exam_certifications.all()],
        "updated_at": level.updated_at.isoformat(),
    }


def _application_result_badge(status):
    if status == ScholarshipApplication.STATUS_ACCEPTED:
        return "accepted"
    if status == ScholarshipApplication.STATUS_REJECTED:
        return "rejected"
    return "pending"


def _serialize_application_document(item):
    return {
        "id": item.id,
        "title": item.title,
        "document_type": item.document_type,
        "document_type_label": item.get_document_type_display(),
        "file_url": item.file.url if item.file else "",
        "file_name": item.file.name.split("/")[-1] if item.file else "",
        "version": item.version,
        "notes": item.notes,
        "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
        "updated_at": item.updated_at.isoformat(),
    }


def _serialize_scholarship_requirement(req):
    return {
        "id": req.id,
        "scholarship_id": req.scholarship_id,
        "requirement_name": req.requirement_name,
        "is_required": req.is_required,
        "is_completed": req.is_completed,
        "linked_document_id": req.linked_document_id,
        "linked_document_title": req.linked_document.title if req.linked_document_id else "",
        "sort_order": req.sort_order,
    }


def _serialize_scholarship(item):
    app = getattr(item, "application", None)
    requirements = [_serialize_scholarship_requirement(req) for req in item.requirements.select_related("linked_document").all()]
    completed = len([req for req in requirements if req["is_completed"]])
    total = len(requirements)
    progress_pct = int((completed / total) * 100) if total else 0
    return {
        "id": item.id,
        "name": item.name,
        "country": item.country,
        "university": item.university,
        "field_of_study": item.field_of_study,
        "degree_level": item.degree_level,
        "official_website": item.official_website,
        "application_deadline": item.application_deadline.isoformat() if item.application_deadline else None,
        "tuition_coverage": item.tuition_coverage,
        "monthly_stipend": _to_money(item.monthly_stipend) if item.monthly_stipend is not None else None,
        "travel_coverage": item.travel_coverage,
        "accommodation": item.accommodation,
        "other_benefits": item.other_benefits,
        "is_active": item.is_active,
        "requirements": requirements,
        "requirements_completed": completed,
        "requirements_total": total,
        "progress_pct": progress_pct,
        "application": {
            "id": app.id,
            "status": app.status,
            "status_label": app.get_status_display(),
            "result_badge": _application_result_badge(app.status),
            "is_submitted": app.is_submitted,
            "submission_date": app.submission_date.isoformat() if app.submission_date else None,
            "application_id": app.application_id,
            "portal_link": app.portal_link,
            "notes": app.notes,
        } if app else None,
    }


def _compute_education_deadline_alerts():
    today = date.today()
    alerts = []
    for scholarship in Scholarship.objects.filter(is_active=True):
        if not scholarship.application_deadline:
            continue
        days = (scholarship.application_deadline - today).days
        if days < 0:
            continue
        if days <= 45:
            alerts.append(
                {
                    "type": "scholarship_deadline",
                    "severity": "warning" if days <= 14 else "info",
                    "days_left": days,
                    "message": f"{scholarship.name} deadline in {days} day{'s' if days != 1 else ''}.",
                    "scholarship_id": scholarship.id,
                }
            )

    for item in ApplicationDocument.objects.exclude(expiration_date__isnull=True):
        days = (item.expiration_date - today).days
        if days < 0:
            continue
        if days <= 30:
            alerts.append(
                {
                    "type": "document_expiration",
                    "severity": "warning" if days <= 7 else "info",
                    "days_left": days,
                    "message": f"{item.title} expires in {days} day{'s' if days != 1 else ''}.",
                    "document_id": item.id,
                }
            )

    alerts.sort(key=lambda row: (row["days_left"], row["message"]))
    return alerts[:30]

@require_GET
def education_bootstrap(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    levels = [_serialize_academic_level(item) for item in AcademicLevel.objects.prefetch_related("exam_certifications").all()]
    documents = [_serialize_application_document(item) for item in ApplicationDocument.objects.all()]
    scholarships = [_serialize_scholarship(item) for item in Scholarship.objects.prefetch_related("requirements__linked_document").select_related("application").all()]
    alerts = _compute_education_deadline_alerts()

    return JsonResponse(
        {
            "ok": True,
            "academic_levels": levels,
            "documents": documents,
            "scholarships": scholarships,
            "deadline_alerts": alerts,
            "summary": {
                "levels_count": len(levels),
                "documents_count": len(documents),
                "scholarships_count": len(scholarships),
                "alerts_count": len(alerts),
            },
        }
    )


@require_GET
def education_levels(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    rows = [_serialize_academic_level(item) for item in AcademicLevel.objects.prefetch_related("exam_certifications").all()]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def education_levels_create(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    payload = _parse_request_data(request)

    level_type = (payload.get("level_type") or "").strip()
    if level_type not in {choice[0] for choice in AcademicLevel.LEVEL_CHOICES}:
        return _json_error("Invalid level type")

    status = (payload.get("status") or AcademicLevel.STATUS_PLANNED).strip()
    if status not in {choice[0] for choice in AcademicLevel.STATUS_CHOICES}:
        status = AcademicLevel.STATUS_PLANNED

    item = AcademicLevel.objects.create(
        level_type=level_type,
        status=status,
        school_name=(payload.get("school_name") or "").strip(),
        admission_number=(payload.get("admission_number") or "").strip(),
        location=(payload.get("location") or "").strip(),
        start_year=_optional_int(payload.get("start_year")),
        end_year=_optional_int(payload.get("end_year")),
        subjects_taken=(payload.get("subjects_taken") or "").strip(),
        grades=(payload.get("grades") or "").strip(),
        certification_exam_completed=_bool_value(payload.get("certification_exam_completed")),
        university_name=(payload.get("university_name") or "").strip(),
        country=(payload.get("country") or "").strip(),
        degree=(payload.get("degree") or "").strip(),
        major_program=(payload.get("major_program") or "").strip(),
        expected_graduation_year=_optional_int(payload.get("expected_graduation_year")),
        student_number=(payload.get("student_number") or "").strip(),
        gpa=(payload.get("gpa") or "").strip(),
        research_topic=(payload.get("research_topic") or "").strip(),
        internships=(payload.get("internships") or "").strip(),
        clubs_activities=(payload.get("clubs_activities") or "").strip(),
        awards=(payload.get("awards") or "").strip(),
        notes=(payload.get("notes") or "").strip(),
    )
    if request.FILES.get("certificate_file"):
        item.certificate_file = request.FILES.get("certificate_file")
    if request.FILES.get("transcript_file"):
        item.transcript_file = request.FILES.get("transcript_file")
    item.save()
    return JsonResponse({"ok": True, "level": _serialize_academic_level(item)}, status=201)


@require_POST
def education_levels_update(request, level_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(AcademicLevel, id=level_id)
    payload = _parse_request_data(request)

    level_type = (payload.get("level_type") or item.level_type).strip()
    if level_type in {choice[0] for choice in AcademicLevel.LEVEL_CHOICES}:
        item.level_type = level_type

    status = (payload.get("status") or item.status).strip()
    if status in {choice[0] for choice in AcademicLevel.STATUS_CHOICES}:
        item.status = status

    fields = [
        "school_name",
        "admission_number",
        "location",
        "subjects_taken",
        "grades",
        "university_name",
        "country",
        "degree",
        "major_program",
        "student_number",
        "gpa",
        "research_topic",
        "internships",
        "clubs_activities",
        "awards",
        "notes",
    ]
    for field in fields:
        if field in payload:
            setattr(item, field, (payload.get(field) or "").strip())

    if "start_year" in payload:
        item.start_year = _optional_int(payload.get("start_year"))
    if "end_year" in payload:
        item.end_year = _optional_int(payload.get("end_year"))
    if "expected_graduation_year" in payload:
        item.expected_graduation_year = _optional_int(payload.get("expected_graduation_year"))
    if "certification_exam_completed" in payload:
        item.certification_exam_completed = _bool_value(payload.get("certification_exam_completed"), item.certification_exam_completed)

    if request.FILES.get("certificate_file"):
        item.certificate_file = request.FILES.get("certificate_file")
    if request.FILES.get("transcript_file"):
        item.transcript_file = request.FILES.get("transcript_file")

    item.save()
    return JsonResponse({"ok": True, "level": _serialize_academic_level(item)})


@require_POST
def education_levels_delete(request, level_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(AcademicLevel, id=level_id)
    item.delete()
    return JsonResponse({"ok": True})


@require_GET
def education_exams(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    rows = [_serialize_exam(item) for item in ExamCertification.objects.select_related("academic_level").all()]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def education_exams_create(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    payload = _parse_request_data(request)

    try:
        level_id = int(payload.get("academic_level_id"))
    except (TypeError, ValueError):
        level_id = None
    level = AcademicLevel.objects.filter(id=level_id).first()
    if not level:
        return _json_error("Academic level is required")

    exam_name = (payload.get("exam_name") or "").strip()
    if not exam_name:
        return _json_error("Exam name is required")

    item = ExamCertification.objects.create(
        academic_level=level,
        exam_name=exam_name,
        exam_year=_optional_int(payload.get("exam_year")),
        candidate_number=(payload.get("candidate_number") or "").strip(),
        grade_score=(payload.get("grade_score") or "").strip(),
        notes=(payload.get("notes") or "").strip(),
    )
    if request.FILES.get("certificate_file"):
        item.certificate_file = request.FILES.get("certificate_file")
        item.save(update_fields=["certificate_file", "updated_at"])

    if "certification_exam_completed" in payload:
        level.certification_exam_completed = _bool_value(payload.get("certification_exam_completed"), True)
    else:
        level.certification_exam_completed = True
    level.save(update_fields=["certification_exam_completed", "updated_at"])
    return JsonResponse({"ok": True, "exam": _serialize_exam(item)}, status=201)


@require_POST
def education_exams_update(request, exam_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ExamCertification, id=exam_id)
    payload = _parse_request_data(request)

    if "academic_level_id" in payload:
        try:
            level_id = int(payload.get("academic_level_id"))
        except (TypeError, ValueError):
            level_id = None
        level = AcademicLevel.objects.filter(id=level_id).first()
        if level:
            item.academic_level = level

    if "exam_name" in payload:
        item.exam_name = (payload.get("exam_name") or item.exam_name).strip()
    if "exam_year" in payload:
        item.exam_year = _optional_int(payload.get("exam_year"))
    if "candidate_number" in payload:
        item.candidate_number = (payload.get("candidate_number") or "").strip()
    if "grade_score" in payload:
        item.grade_score = (payload.get("grade_score") or "").strip()
    if "notes" in payload:
        item.notes = (payload.get("notes") or "").strip()
    if request.FILES.get("certificate_file"):
        item.certificate_file = request.FILES.get("certificate_file")
    item.save()
    return JsonResponse({"ok": True, "exam": _serialize_exam(item)})


@require_POST
def education_exams_delete(request, exam_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ExamCertification, id=exam_id)
    item.delete()
    return JsonResponse({"ok": True})


@require_GET
def education_documents(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    rows = [_serialize_application_document(item) for item in ApplicationDocument.objects.all()]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def education_documents_create(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    payload = _parse_request_data(request)

    title = (payload.get("title") or "").strip()
    if not title:
        return _json_error("Document title is required")
    doc_type = (payload.get("document_type") or ApplicationDocument.TYPE_OTHER).strip()
    if doc_type not in {choice[0] for choice in ApplicationDocument.DOCUMENT_TYPE_CHOICES}:
        return _json_error("Invalid document type")

    uploaded = request.FILES.get("file")
    if not uploaded:
        return _json_error("Document file is required")
    validation_error = _validate_uploaded_file(uploaded)
    if validation_error:
        return _json_error(validation_error)

    item = ApplicationDocument.objects.create(
        title=title,
        document_type=doc_type,
        file=uploaded,
        version=(payload.get("version") or "v1").strip()[:40],
        notes=(payload.get("notes") or "").strip(),
        expiration_date=_parse_date(payload.get("expiration_date")),
    )
    return JsonResponse({"ok": True, "document": _serialize_application_document(item)}, status=201)


@require_POST
def education_documents_update(request, document_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ApplicationDocument, id=document_id)
    payload = _parse_request_data(request)

    if "title" in payload:
        item.title = (payload.get("title") or item.title).strip()
    if "document_type" in payload:
        doc_type = (payload.get("document_type") or item.document_type).strip()
        if doc_type in {choice[0] for choice in ApplicationDocument.DOCUMENT_TYPE_CHOICES}:
            item.document_type = doc_type
    if "version" in payload:
        item.version = (payload.get("version") or item.version).strip()[:40]
    if "notes" in payload:
        item.notes = (payload.get("notes") or "").strip()
    if "expiration_date" in payload:
        item.expiration_date = _parse_date(payload.get("expiration_date"))

    uploaded = request.FILES.get("file")
    if uploaded:
        validation_error = _validate_uploaded_file(uploaded)
        if validation_error:
            return _json_error(validation_error)
        item.file = uploaded

    item.save()
    return JsonResponse({"ok": True, "document": _serialize_application_document(item)})


@require_POST
def education_documents_delete(request, document_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ApplicationDocument, id=document_id)
    item.delete()
    return JsonResponse({"ok": True})


@require_GET
def education_scholarships(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    rows = [_serialize_scholarship(item) for item in Scholarship.objects.prefetch_related("requirements__linked_document").select_related("application").all()]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def education_scholarships_create(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)

    name = (payload.get("name") or "").strip()
    if not name:
        return _json_error("Scholarship name is required")

    item = Scholarship.objects.create(
        name=name,
        country=(payload.get("country") or "").strip(),
        university=(payload.get("university") or "").strip(),
        field_of_study=(payload.get("field_of_study") or "").strip(),
        degree_level=(payload.get("degree_level") or "").strip(),
        official_website=(payload.get("official_website") or "").strip(),
        application_deadline=_parse_date(payload.get("application_deadline")),
        tuition_coverage=(payload.get("tuition_coverage") or "").strip(),
        monthly_stipend=_safe_decimal(payload.get("monthly_stipend"), None),
        travel_coverage=_bool_value(payload.get("travel_coverage")),
        accommodation=_bool_value(payload.get("accommodation")),
        other_benefits=(payload.get("other_benefits") or "").strip(),
        is_active=_bool_value(payload.get("is_active"), True),
    )
    ScholarshipApplication.objects.create(
        scholarship=item,
        status=ScholarshipApplication.STATUS_RESEARCHING,
        is_submitted=False,
    )
    return JsonResponse({"ok": True, "scholarship": _serialize_scholarship(item)}, status=201)


@require_POST
def education_scholarships_update(request, scholarship_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(Scholarship, id=scholarship_id)
    payload = _parse_json(request)

    text_fields = [
        "name",
        "country",
        "university",
        "field_of_study",
        "degree_level",
        "official_website",
        "tuition_coverage",
        "other_benefits",
    ]
    for field in text_fields:
        if field in payload:
            setattr(item, field, (payload.get(field) or "").strip())
    if "application_deadline" in payload:
        item.application_deadline = _parse_date(payload.get("application_deadline"))
    if "monthly_stipend" in payload:
        item.monthly_stipend = _safe_decimal(payload.get("monthly_stipend"), None)
    if "travel_coverage" in payload:
        item.travel_coverage = _bool_value(payload.get("travel_coverage"), item.travel_coverage)
    if "accommodation" in payload:
        item.accommodation = _bool_value(payload.get("accommodation"), item.accommodation)
    if "is_active" in payload:
        item.is_active = _bool_value(payload.get("is_active"), item.is_active)
    item.save()
    return JsonResponse({"ok": True, "scholarship": _serialize_scholarship(item)})


@require_POST
def education_scholarships_delete(request, scholarship_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(Scholarship, id=scholarship_id)
    item.delete()
    return JsonResponse({"ok": True})


@require_POST
def education_requirements_create(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)

    scholarship = Scholarship.objects.filter(id=payload.get("scholarship_id")).first()
    if not scholarship:
        return _json_error("Scholarship is required")
    requirement_name = (payload.get("requirement_name") or "").strip()
    if not requirement_name:
        return _json_error("Requirement name is required")

    linked_document = ApplicationDocument.objects.filter(id=payload.get("linked_document_id")).first() if payload.get("linked_document_id") else None
    item = ScholarshipRequirement.objects.create(
        scholarship=scholarship,
        requirement_name=requirement_name,
        is_required=_bool_value(payload.get("is_required"), True),
        is_completed=_bool_value(payload.get("is_completed"), False),
        linked_document=linked_document,
        sort_order=_optional_int(payload.get("sort_order")) or 0,
    )
    return JsonResponse({"ok": True, "requirement": _serialize_scholarship_requirement(item)}, status=201)


@require_POST
def education_requirements_update(request, requirement_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ScholarshipRequirement, id=requirement_id)
    payload = _parse_json(request)

    if "requirement_name" in payload:
        item.requirement_name = (payload.get("requirement_name") or item.requirement_name).strip()
    if "is_required" in payload:
        item.is_required = _bool_value(payload.get("is_required"), item.is_required)
    if "is_completed" in payload:
        item.is_completed = _bool_value(payload.get("is_completed"), item.is_completed)
    if "sort_order" in payload:
        item.sort_order = _optional_int(payload.get("sort_order")) or item.sort_order
    if "linked_document_id" in payload:
        item.linked_document = ApplicationDocument.objects.filter(id=payload.get("linked_document_id")).first() if payload.get("linked_document_id") else None
    item.save()
    return JsonResponse({"ok": True, "requirement": _serialize_scholarship_requirement(item)})


@require_POST
def education_requirements_delete(request, requirement_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ScholarshipRequirement, id=requirement_id)
    item.delete()
    return JsonResponse({"ok": True})


@require_POST
def education_requirements_toggle(request, requirement_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ScholarshipRequirement, id=requirement_id)
    item.is_completed = not item.is_completed
    item.save(update_fields=["is_completed", "updated_at"])
    return JsonResponse({"ok": True, "requirement": _serialize_scholarship_requirement(item)})


@require_POST
def education_applications_create(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)
    scholarship = Scholarship.objects.filter(id=payload.get("scholarship_id")).first()
    if not scholarship:
        return _json_error("Scholarship is required")
    if ScholarshipApplication.objects.filter(scholarship=scholarship).exists():
        return _json_error("Application already exists for this scholarship", status=409)
    item = ScholarshipApplication.objects.create(scholarship=scholarship)
    return JsonResponse({"ok": True, "application": {"id": item.id, "scholarship_id": scholarship.id}}, status=201)


@require_POST
def education_applications_update(request, application_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ScholarshipApplication, id=application_id)
    payload = _parse_json(request)

    if "status" in payload:
        status = (payload.get("status") or "").strip()
        if status in {choice[0] for choice in ScholarshipApplication.STATUS_CHOICES}:
            item.status = status
    if "is_submitted" in payload:
        item.is_submitted = _bool_value(payload.get("is_submitted"), item.is_submitted)
    if "submission_date" in payload:
        item.submission_date = _parse_date(payload.get("submission_date"))
    if "application_id" in payload:
        item.application_id = (payload.get("application_id") or "").strip()
    if "portal_link" in payload:
        item.portal_link = (payload.get("portal_link") or "").strip()
    if "notes" in payload:
        item.notes = (payload.get("notes") or "").strip()

    item.save()
    return JsonResponse(
        {
            "ok": True,
            "application": {
                "id": item.id,
                "status": item.status,
                "status_label": item.get_status_display(),
                "result_badge": _application_result_badge(item.status),
                "is_submitted": item.is_submitted,
                "submission_date": item.submission_date.isoformat() if item.submission_date else None,
                "application_id": item.application_id,
                "portal_link": item.portal_link,
                "notes": item.notes,
            },
        }
    )


@require_POST
def education_applications_delete(request, application_id):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    item = get_object_or_404(ScholarshipApplication, id=application_id)
    item.delete()
    return JsonResponse({"ok": True})


@require_GET
def education_deadline_alerts(request):
    auth_error = _require_education_access(request)
    if auth_error:
        return auth_error
    return JsonResponse({"ok": True, "rows": _compute_education_deadline_alerts()})


# -----------------------------
# Personal identity vault APIs
# -----------------------------


PERSONAL_FILE_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\-\s]{6,20}$")
URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


def _validate_personal_file(uploaded_file):
    if uploaded_file is None:
        return "No file provided"
    if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        return "File is too large. Maximum size is 10MB"
    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in PERSONAL_FILE_ALLOWED_EXTENSIONS:
        return "Unsupported file type. Allowed: PDF, JPG, PNG"
    return None


def _validate_profile_photo(uploaded_file):
    if uploaded_file is None:
        return "No photo provided"
    if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        return "Photo is too large. Maximum size is 10MB"
    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png"}:
        return "Unsupported photo type. Allowed: JPG, PNG"
    return None


def _is_valid_email(value):
    text = (value or "").strip()
    if not text:
        return True
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text))


def _is_valid_phone(value):
    text = (value or "").strip()
    if not text:
        return True
    return bool(PHONE_PATTERN.fullmatch(text))


def _is_valid_url(value):
    text = (value or "").strip()
    if not text:
        return True
    return bool(URL_PATTERN.match(text))


def _vault_key_bytes():
    return hashlib.sha256(f"{settings.SECRET_KEY}|personal-vault|v1".encode("utf-8")).digest()


def _personal_keystream(key_bytes, nonce, length):
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        block = hashlib.sha256(key_bytes + nonce + counter.to_bytes(4, "big")).digest()
        stream.extend(block)
        counter += 1
    return bytes(stream[:length])


def _encrypt_personal_sensitive(value):
    text = (value or "").strip()
    if not text:
        return ""
    raw = text.encode("utf-8")
    key = _vault_key_bytes()
    nonce = os.urandom(16)
    stream = _personal_keystream(key, nonce, len(raw))
    cipher = bytes(a ^ b for a, b in zip(raw, stream))
    mac = hmac.new(key, nonce + cipher, hashlib.sha256).digest()[:16]
    token = nonce + mac + cipher
    return base64.urlsafe_b64encode(token).decode("ascii")


def _decrypt_personal_sensitive(token):
    if not token:
        return ""
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii"))
        if len(decoded) < 33:
            return ""
        nonce = decoded[:16]
        mac = decoded[16:32]
        cipher = decoded[32:]
        key = _vault_key_bytes()
        expected = hmac.new(key, nonce + cipher, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(mac, expected):
            return ""
        stream = _personal_keystream(key, nonce, len(cipher))
        plain = bytes(a ^ b for a, b in zip(cipher, stream))
        return plain.decode("utf-8")
    except Exception:
        return ""


def _get_or_create_personal_vault():
    vault = PersonalIdentityVault.objects.first()
    if not vault:
        profile = UserProfile.objects.first()
        first_name = ""
        last_name = ""
        if profile and profile.display_name:
            parts = profile.display_name.split()
            first_name = parts[0] if parts else ""
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""
        vault = PersonalIdentityVault.objects.create(first_name=first_name, last_name=last_name, nationality="Kenyan")
    contact, _ = ContactInfo.objects.get_or_create(vault=vault)
    identity_docs, _ = IdentityDocuments.objects.get_or_create(vault=vault)
    social, _ = SocialProfiles.objects.get_or_create(vault=vault)
    return vault, contact, identity_docs, social


def _serialize_personal_identity(vault):
    return {
        "first_name": vault.first_name,
        "last_name": vault.last_name,
        "dob": vault.dob.isoformat() if vault.dob else None,
        "gender": vault.gender,
        "nationality": vault.nationality,
        "languages": vault.languages or [],
        "profile_photo_url": vault.profile_photo.url if vault.profile_photo else "",
    }


def _serialize_contact_info(contact):
    return {
        "primary_email": contact.primary_email,
        "secondary_email": contact.secondary_email,
        "additional_emails": contact.additional_emails or [],
        "primary_phone": contact.primary_phone,
        "secondary_phone": contact.secondary_phone,
        "other_phone_numbers": contact.other_phone_numbers or [],
        "home_address": contact.home_address,
        "city": contact.city,
        "country": contact.country,
        "postal_code": contact.postal_code,
    }


def _serialize_identity_documents(identity_docs):
    return {
        "national_id": _decrypt_personal_sensitive(identity_docs.national_id_encrypted),
        "passport_number": _decrypt_personal_sensitive(identity_docs.passport_number_encrypted),
        "passport_expiry": identity_docs.passport_expiry.isoformat() if identity_docs.passport_expiry else None,
        "drivers_license": _decrypt_personal_sensitive(identity_docs.drivers_license_encrypted),
        "student_id": _decrypt_personal_sensitive(identity_docs.student_id_encrypted),
    }


def _serialize_identity_file(item):
    return {
        "id": item.id,
        "file_type": item.file_type,
        "file_type_label": item.get_file_type_display(),
        "file_url": item.file.url if item.file else "",
        "file_name": item.original_name or (item.file.name.split("/")[-1] if item.file else ""),
        "file_size": item.file_size,
        "updated_at": item.updated_at.isoformat(),
    }


def _serialize_digital_account(item):
    return {
        "id": item.id,
        "platform": item.platform,
        "platform_label": item.get_platform_display(),
        "custom_platform": item.custom_platform,
        "username": item.username,
        "email_used": item.email_used,
        "profile_link": item.profile_link,
        "notes": item.notes,
    }


def _serialize_social_profiles(item):
    return {
        "linkedin": item.linkedin,
        "twitter_x": item.twitter_x,
        "instagram": item.instagram,
        "github": item.github,
        "portfolio_website": item.portfolio_website,
        "personal_blog": item.personal_blog,
        "youtube_channel": item.youtube_channel,
    }


def _serialize_password_reference(item):
    return {
        "id": item.id,
        "platform": item.platform,
        "username": item.username,
        "email_used": item.email_used,
        "password_hint": item.password_hint,
        "two_factor_enabled": item.two_factor_enabled,
        "backup_codes_location": item.backup_codes_location,
        "password_manager": item.password_manager,
        "password_manager_label": item.get_password_manager_display(),
        "notes": item.notes,
    }


def _compute_personal_completion(vault, contact, identity_docs, files, digital_accounts, social, password_refs):
    def has_any(values):
        return any(bool(v) for v in values)

    step_checks = []

    step1 = has_any([vault.first_name, vault.last_name, vault.dob, vault.nationality, vault.profile_photo, vault.languages])
    step_checks.append(step1)

    step2 = has_any([contact.primary_email, contact.primary_phone, contact.city, contact.country]) and _is_valid_email(contact.primary_email)
    step_checks.append(step2)

    step3 = has_any(
        [
            _decrypt_personal_sensitive(identity_docs.national_id_encrypted),
            _decrypt_personal_sensitive(identity_docs.passport_number_encrypted),
            identity_docs.passport_expiry,
            _decrypt_personal_sensitive(identity_docs.drivers_license_encrypted),
            _decrypt_personal_sensitive(identity_docs.student_id_encrypted),
        ]
    ) and len(files) > 0
    step_checks.append(step3)

    step4 = len(digital_accounts) > 0
    step_checks.append(step4)

    social_values = [social.linkedin, social.twitter_x, social.instagram, social.github, social.portfolio_website, social.personal_blog, social.youtube_channel]
    step5 = has_any(social_values)
    step_checks.append(step5)

    step6 = len(password_refs) > 0
    step_checks.append(step6)

    completed_count = len([flag for flag in step_checks if flag])
    score = int((completed_count / 6) * 100)

    suggestions = []
    if not step1:
        suggestions.append("Add your basic identity details and profile photo.")
    if not step2:
        suggestions.append("Add a primary contact email and phone number.")
    if not step3:
        suggestions.append("Upload identity documents and add passport details.")
    if not step4:
        suggestions.append("Add your key digital accounts.")
    if not step5:
        suggestions.append("Add public social profile links.")
    if not step6:
        suggestions.append("Add password reference entries with 2FA status.")

    step_labels = [
        "Basic Identity",
        "Contact Information",
        "Identity Documents",
        "Digital Accounts",
        "Public Social Profiles",
        "Security References",
    ]
    step_status = []
    for idx, completed in enumerate(step_checks, start=1):
        icon = "✓" if completed else "○"
        status = "completed" if completed else "not_started"
        if not completed and idx == completed_count + 1:
            icon = "•"
            status = "in_progress"
        step_status.append({"step": idx, "label": step_labels[idx - 1], "icon": icon, "status": status})

    return score, step_status, suggestions


def _personal_document_expiry_alerts(identity_docs):
    alerts = []
    if identity_docs.passport_expiry:
        today = date.today()
        diff = (identity_docs.passport_expiry - today).days
        if diff >= 0 and diff <= 180:
            alerts.append(
                {
                    "type": "passport_expiry",
                    "severity": "warning" if diff <= 60 else "info",
                    "message": f"Passport expires in {diff} day{'s' if diff != 1 else ''}.",
                    "days_left": diff,
                }
            )
    return alerts


@require_GET
def personal_vault_bootstrap(request):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    vault, contact, identity_docs, social = _get_or_create_personal_vault()
    files = list(IdentityUploadedFile.objects.filter(vault=vault))
    digital_accounts = list(DigitalAccounts.objects.filter(vault=vault))
    password_refs = list(PasswordReferences.objects.filter(vault=vault))
    completion_score, step_status, suggestions = _compute_personal_completion(
        vault, contact, identity_docs, files, digital_accounts, social, password_refs
    )

    return JsonResponse(
        {
            "ok": True,
            "identity": _serialize_personal_identity(vault),
            "contact": _serialize_contact_info(contact),
            "identity_documents": _serialize_identity_documents(identity_docs),
            "uploaded_files": [_serialize_identity_file(item) for item in files],
            "digital_accounts": [_serialize_digital_account(item) for item in digital_accounts],
            "social_profiles": _serialize_social_profiles(social),
            "password_references": [_serialize_password_reference(item) for item in password_refs],
            "completion_score": completion_score,
            "step_status": step_status,
            "suggestions": suggestions,
            "expiry_alerts": _personal_document_expiry_alerts(identity_docs),
        }
    )


@require_POST
def personal_vault_step1_save(request):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    payload = _parse_request_data(request)
    vault, _, _, _ = _get_or_create_personal_vault()

    if "first_name" in payload:
        vault.first_name = (payload.get("first_name") or "").strip()
    if "last_name" in payload:
        vault.last_name = (payload.get("last_name") or "").strip()
    if "dob" in payload:
        vault.dob = _parse_date(payload.get("dob"))
    if "gender" in payload:
        gender = (payload.get("gender") or "").strip()
        if not gender:
            vault.gender = ""
        elif gender in {choice[0] for choice in PersonalIdentityVault.GENDER_CHOICES}:
            vault.gender = gender
    if "nationality" in payload:
        vault.nationality = (payload.get("nationality") or "").strip()
    if "languages" in payload:
        vault.languages = _split_tags(payload.get("languages"))

    photo = request.FILES.get("profile_photo")
    if photo:
        validation_error = _validate_profile_photo(photo)
        if validation_error:
            return _json_error(validation_error)
        vault.profile_photo = photo

    vault.save()
    return JsonResponse({"ok": True, "identity": _serialize_personal_identity(vault)})


@require_POST
def personal_vault_step2_save(request):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)
    vault, contact, _, _ = _get_or_create_personal_vault()
    _ = vault

    primary_email = (payload.get("primary_email") or "").strip()
    secondary_email = (payload.get("secondary_email") or "").strip()
    primary_phone = (payload.get("primary_phone") or "").strip()
    secondary_phone = (payload.get("secondary_phone") or "").strip()

    email_values = [primary_email, secondary_email] + _split_tags(payload.get("additional_emails"))
    for email in email_values:
        if email and not _is_valid_email(email):
            return _json_error(f"Invalid email format: {email}")

    phone_values = [primary_phone, secondary_phone] + _split_tags(payload.get("other_phone_numbers"))
    for phone in phone_values:
        if phone and not _is_valid_phone(phone):
            return _json_error(f"Invalid phone format: {phone}")

    contact.primary_email = primary_email
    contact.secondary_email = secondary_email
    contact.additional_emails = _split_tags(payload.get("additional_emails"))
    contact.primary_phone = primary_phone
    contact.secondary_phone = secondary_phone
    contact.other_phone_numbers = _split_tags(payload.get("other_phone_numbers"))
    contact.home_address = (payload.get("home_address") or "").strip()
    contact.city = (payload.get("city") or "").strip()
    contact.country = (payload.get("country") or "").strip()
    contact.postal_code = (payload.get("postal_code") or "").strip()
    contact.save()

    return JsonResponse({"ok": True, "contact": _serialize_contact_info(contact)})


@require_POST
def personal_vault_step3_save(request):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)
    _, _, identity_docs, _ = _get_or_create_personal_vault()

    if "national_id" in payload:
        identity_docs.national_id_encrypted = _encrypt_personal_sensitive(payload.get("national_id"))
    if "passport_number" in payload:
        identity_docs.passport_number_encrypted = _encrypt_personal_sensitive(payload.get("passport_number"))
    if "passport_expiry" in payload:
        identity_docs.passport_expiry = _parse_date(payload.get("passport_expiry"))
    if "drivers_license" in payload:
        identity_docs.drivers_license_encrypted = _encrypt_personal_sensitive(payload.get("drivers_license"))
    if "student_id" in payload:
        identity_docs.student_id_encrypted = _encrypt_personal_sensitive(payload.get("student_id"))
    identity_docs.save()

    return JsonResponse({"ok": True, "identity_documents": _serialize_identity_documents(identity_docs)})


@require_GET
def personal_vault_identity_files(request):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    vault, _, _, _ = _get_or_create_personal_vault()
    rows = [_serialize_identity_file(item) for item in IdentityUploadedFile.objects.filter(vault=vault)]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def personal_vault_identity_file_upload(request):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    payload = _parse_request_data(request)
    vault, _, _, _ = _get_or_create_personal_vault()
    file_type = (payload.get("file_type") or IdentityUploadedFile.TYPE_OTHER).strip()
    if file_type not in {choice[0] for choice in IdentityUploadedFile.FILE_TYPE_CHOICES}:
        return _json_error("Invalid identity document type")

    uploaded_file = request.FILES.get("file")
    validation_error = _validate_personal_file(uploaded_file)
    if validation_error:
        return _json_error(validation_error)

    item = IdentityUploadedFile.objects.create(
        vault=vault,
        file_type=file_type,
        file=uploaded_file,
        original_name=uploaded_file.name,
        file_size=uploaded_file.size,
    )
    return JsonResponse({"ok": True, "file": _serialize_identity_file(item)}, status=201)


@require_POST
def personal_vault_identity_file_delete(request, file_id):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    vault, _, _, _ = _get_or_create_personal_vault()
    item = get_object_or_404(IdentityUploadedFile, id=file_id, vault=vault)
    item.delete()
    return JsonResponse({"ok": True})


@require_GET
def personal_vault_digital_accounts(request):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    vault, _, _, _ = _get_or_create_personal_vault()
    rows = [_serialize_digital_account(item) for item in DigitalAccounts.objects.filter(vault=vault)]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def personal_vault_digital_accounts_create(request):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)
    vault, _, _, _ = _get_or_create_personal_vault()

    platform = (payload.get("platform") or "").strip()
    if platform not in {choice[0] for choice in DigitalAccounts.PLATFORM_CHOICES}:
        return _json_error("Invalid platform")
    profile_link = (payload.get("profile_link") or "").strip()
    if not _is_valid_url(profile_link):
        return _json_error("Invalid profile URL")
    email_used = (payload.get("email_used") or "").strip()
    if email_used and not _is_valid_email(email_used):
        return _json_error("Invalid account email format")

    item = DigitalAccounts.objects.create(
        vault=vault,
        platform=platform,
        custom_platform=(payload.get("custom_platform") or "").strip(),
        username=(payload.get("username") or "").strip(),
        email_used=email_used,
        profile_link=profile_link,
        notes=(payload.get("notes") or "").strip(),
    )
    return JsonResponse({"ok": True, "account": _serialize_digital_account(item)}, status=201)


@require_POST
def personal_vault_digital_accounts_update(request, account_id):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)
    vault, _, _, _ = _get_or_create_personal_vault()
    item = get_object_or_404(DigitalAccounts, id=account_id, vault=vault)

    platform = (payload.get("platform") if "platform" in payload else item.platform or "").strip()
    if platform not in {choice[0] for choice in DigitalAccounts.PLATFORM_CHOICES}:
        return _json_error("Invalid platform")
    profile_link = (payload.get("profile_link") if "profile_link" in payload else item.profile_link or "").strip()
    if not _is_valid_url(profile_link):
        return _json_error("Invalid profile URL")
    email_used = (payload.get("email_used") if "email_used" in payload else item.email_used or "").strip()
    if email_used and not _is_valid_email(email_used):
        return _json_error("Invalid account email format")

    item.platform = platform
    item.custom_platform = (payload.get("custom_platform") if "custom_platform" in payload else item.custom_platform or "").strip()
    item.username = (payload.get("username") if "username" in payload else item.username or "").strip()
    item.email_used = email_used
    item.profile_link = profile_link
    item.notes = (payload.get("notes") if "notes" in payload else item.notes or "").strip()
    item.save()
    return JsonResponse({"ok": True, "account": _serialize_digital_account(item)})


@require_POST
def personal_vault_digital_accounts_delete(request, account_id):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    vault, _, _, _ = _get_or_create_personal_vault()
    item = get_object_or_404(DigitalAccounts, id=account_id, vault=vault)
    item.delete()
    return JsonResponse({"ok": True})


@require_POST
def personal_vault_social_profiles_save(request):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)
    _, _, _, social = _get_or_create_personal_vault()

    url_fields = [
        "linkedin",
        "twitter_x",
        "instagram",
        "github",
        "portfolio_website",
        "personal_blog",
        "youtube_channel",
    ]
    for field in url_fields:
        value = (payload.get(field) or "").strip()
        if value and not _is_valid_url(value):
            return _json_error(f"Invalid URL for {field.replace('_', ' ')}")
        setattr(social, field, value)
    social.save()
    return JsonResponse({"ok": True, "social_profiles": _serialize_social_profiles(social)})


@require_GET
def personal_vault_password_references(request):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    vault, _, _, _ = _get_or_create_personal_vault()
    rows = [_serialize_password_reference(item) for item in PasswordReferences.objects.filter(vault=vault)]
    return JsonResponse({"ok": True, "rows": rows})


@require_POST
def personal_vault_password_references_create(request):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)
    vault, _, _, _ = _get_or_create_personal_vault()
    manager = (payload.get("password_manager") or PasswordReferences.MANAGER_BITWARDEN).strip()
    if manager not in {choice[0] for choice in PasswordReferences.PASSWORD_MANAGER_CHOICES}:
        return _json_error("Invalid password manager")
    email_used = (payload.get("email_used") or "").strip()
    if email_used and not _is_valid_email(email_used):
        return _json_error("Invalid email format")
    item = PasswordReferences.objects.create(
        vault=vault,
        platform=(payload.get("platform") or "").strip(),
        username=(payload.get("username") or "").strip(),
        email_used=email_used,
        password_hint=(payload.get("password_hint") or "").strip(),
        two_factor_enabled=_bool_value(payload.get("two_factor_enabled"), False),
        backup_codes_location=(payload.get("backup_codes_location") or "").strip(),
        password_manager=manager,
        notes=(payload.get("notes") or "").strip(),
    )
    return JsonResponse({"ok": True, "reference": _serialize_password_reference(item)}, status=201)


@require_POST
def personal_vault_password_references_update(request, reference_id):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    payload = _parse_json(request)
    vault, _, _, _ = _get_or_create_personal_vault()
    item = get_object_or_404(PasswordReferences, id=reference_id, vault=vault)
    manager = (payload.get("password_manager") if "password_manager" in payload else item.password_manager or "").strip()
    if manager not in {choice[0] for choice in PasswordReferences.PASSWORD_MANAGER_CHOICES}:
        return _json_error("Invalid password manager")
    email_used = (payload.get("email_used") if "email_used" in payload else item.email_used or "").strip()
    if email_used and not _is_valid_email(email_used):
        return _json_error("Invalid email format")

    item.platform = (payload.get("platform") if "platform" in payload else item.platform or "").strip()
    item.username = (payload.get("username") if "username" in payload else item.username or "").strip()
    item.email_used = email_used
    item.password_hint = (payload.get("password_hint") if "password_hint" in payload else item.password_hint or "").strip()
    item.two_factor_enabled = _bool_value(payload.get("two_factor_enabled"), item.two_factor_enabled)
    item.backup_codes_location = (payload.get("backup_codes_location") if "backup_codes_location" in payload else item.backup_codes_location or "").strip()
    item.password_manager = manager
    item.notes = (payload.get("notes") if "notes" in payload else item.notes or "").strip()
    item.save()
    return JsonResponse({"ok": True, "reference": _serialize_password_reference(item)})


@require_POST
def personal_vault_password_references_delete(request, reference_id):
    auth_error = _require_personal_vault_access(request)
    if auth_error:
        return auth_error
    vault, _, _, _ = _get_or_create_personal_vault()
    item = get_object_or_404(PasswordReferences, id=reference_id, vault=vault)
    item.delete()
    return JsonResponse({"ok": True})
