from collections import Counter

from django.contrib import messages
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from myos_app.views import _is_htmx_request, _render_page

from .analytics import anime_analytics, global_media_analytics, movies_analytics, series_analytics
from .forms import MediaItemForm, MediaProgressForm
from .models import MediaItem, MediaProgress
from .services import (
    PROGRESS_PREFETCH,
    calculate_completion_rate,
    calculate_watch_time,
    get_animation_stats,
    get_anime_stats,
    get_movies_stats,
    get_series_stats,
)


CATEGORY_ROUTE_MAP = {
    MediaItem.Category.MOVIE: "movies_view",
    MediaItem.Category.SERIES: "series_view",
    MediaItem.Category.ANIME: "anime_view",
    MediaItem.Category.ANIMATION: "animation_view",
}


def _render_media_page(
    request,
    template_name,
    *,
    extra_context=None,
    partial_template=None,
    status=200,
    headers=None,
):
    return _render_page(
        request,
        template_name,
        "media",
        extra_context,
        partial_template=partial_template,
        status=status,
        headers=headers,
    )


def _base_queryset(request):
    queryset = MediaItem.objects.select_related("user")
    if request.user.is_authenticated:
        return queryset.filter(Q(user=request.user) | Q(user__isnull=True))
    return queryset.filter(user__isnull=True)


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _apply_filters(queryset, request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    media_type = (request.GET.get("type") or "").strip()
    platform = (request.GET.get("platform") or "").strip()
    genre = (request.GET.get("genre") or "").strip()
    year = _safe_int(request.GET.get("year"))

    if q:
        queryset = queryset.filter(
            Q(title__icontains=q)
            | Q(genre__icontains=q)
            | Q(studio__icontains=q)
            | Q(platform__icontains=q)
            | Q(country__icontains=q)
        )
    if status in {choice for choice, _ in MediaItem.Status.choices}:
        queryset = queryset.filter(status=status)
    if media_type in {choice for choice, _ in MediaItem.MediaType.choices}:
        queryset = queryset.filter(type=media_type)
    if platform:
        queryset = queryset.filter(platform__icontains=platform)
    if genre:
        queryset = queryset.filter(genre__icontains=genre)
    if year is not None:
        queryset = queryset.filter(year=year)

    return queryset


def _genre_distribution(items):
    counter = Counter()
    for item in items:
        raw = (item.genre or "").strip()
        if not raw:
            continue
        for chunk in [piece.strip() for piece in raw.split(",") if piece.strip()]:
            counter[chunk] += 1
    return [{"genre": genre, "count": count} for genre, count in counter.most_common()]


def _episodes_per_month(progress_queryset):
    rows = (
        progress_queryset.annotate(month=TruncMonth("date_watched"))
        .values("month")
        .annotate(total=Sum("episodes_watched"))
        .order_by("month")
    )
    return [
        {
            "month": row["month"].strftime("%Y-%m") if row["month"] else "",
            "value": int(row["total"] or 0),
        }
        for row in rows
    ]


def _category_route_name(category):
    return CATEGORY_ROUTE_MAP.get(category, "media")


def _filters_context(request):
    return {
        "q": (request.GET.get("q") or "").strip(),
        "status": (request.GET.get("status") or "").strip(),
        "type": (request.GET.get("type") or "").strip(),
        "platform": (request.GET.get("platform") or "").strip(),
        "genre": (request.GET.get("genre") or "").strip(),
        "year": (request.GET.get("year") or "").strip(),
    }


def media_dashboard(request):
    base_qs = _apply_filters(_base_queryset(request), request)
    recent_media = list(
        base_qs.prefetch_related(PROGRESS_PREFETCH).order_by("-date_added", "-id")[:12]
    )

    movies_qs = base_qs.filter(category=MediaItem.Category.MOVIE)
    series_qs = base_qs.filter(category=MediaItem.Category.SERIES)
    anime_qs = base_qs.filter(category=MediaItem.Category.ANIME)
    animation_qs = base_qs.filter(category=MediaItem.Category.ANIMATION)

    global_analytics = global_media_analytics()
    watch_hours = global_analytics.get("total_watch_time", {}).get("hours", 0)

    context = {
        "active_page": "media",
        "recent_media": recent_media,
        "movies_stats": get_movies_stats(movies_qs),
        "series_stats": get_series_stats(series_qs),
        "anime_stats": get_anime_stats(anime_qs),
        "animation_stats": get_animation_stats(animation_qs),
        "global_analytics": global_analytics,
        "watch_time_message": f"You watched {watch_hours:.2f} hours of content this year.",
        "filters": _filters_context(request),
        "status_choices": MediaItem.Status.choices,
        "type_choices": MediaItem.MediaType.choices,
    }
    return _render_media_page(
        request,
        "media/media.html",
        extra_context=context,
        partial_template="media/media_partial.html",
    )


def movies_view(request):
    queryset = _apply_filters(_base_queryset(request).filter(category=MediaItem.Category.MOVIE), request)
    stats = get_movies_stats(queryset)
    context = {
        "active_page": "media",
        "movies": stats["items"],
        "stats": stats,
        "analytics": movies_analytics(),
        "filters": _filters_context(request),
        "status_choices": MediaItem.Status.choices,
    }
    return _render_media_page(
        request,
        "media/movies.html",
        extra_context=context,
        partial_template="media/movies_partial.html",
    )


def series_view(request):
    queryset = _apply_filters(_base_queryset(request).filter(category=MediaItem.Category.SERIES), request)
    stats = get_series_stats(queryset)
    context = {
        "active_page": "media",
        "series": stats["items"],
        "stats": stats,
        "analytics": series_analytics(),
        "filters": _filters_context(request),
        "status_choices": MediaItem.Status.choices,
    }
    return _render_media_page(
        request,
        "media/series.html",
        extra_context=context,
        partial_template="media/series_partial.html",
    )


def anime_view(request):
    queryset = _apply_filters(_base_queryset(request).filter(category=MediaItem.Category.ANIME), request)
    stats = get_anime_stats(queryset)
    items = stats["items"]
    context = {
        "active_page": "media",
        "anime": items,
        "anime_movies": [item for item in items if item.type == MediaItem.MediaType.MOVIE],
        "anime_series": [item for item in items if item.type == MediaItem.MediaType.SERIES],
        "stats": stats,
        "analytics": anime_analytics(),
        "filters": _filters_context(request),
        "status_choices": MediaItem.Status.choices,
        "type_choices": MediaItem.MediaType.choices,
    }
    return _render_media_page(
        request,
        "media/anime.html",
        extra_context=context,
        partial_template="media/anime_partial.html",
    )


def animation_view(request):
    queryset = _apply_filters(_base_queryset(request).filter(category=MediaItem.Category.ANIMATION), request)
    stats = get_animation_stats(queryset)
    items = stats["items"]
    context = {
        "active_page": "media",
        "animation": items,
        "animation_movies": [item for item in items if item.type == MediaItem.MediaType.MOVIE],
        "animation_series": [item for item in items if item.type == MediaItem.MediaType.SERIES],
        "stats": stats,
        "filters": _filters_context(request),
        "status_choices": MediaItem.Status.choices,
        "type_choices": MediaItem.MediaType.choices,
    }
    return _render_media_page(
        request,
        "media/animation.html",
        extra_context=context,
        partial_template="media/animation_partial.html",
    )


@require_http_methods(["GET", "POST"])
def add_media(request):
    initial = {
        key: request.GET.get(key)
        for key in ("category", "type", "status")
        if request.GET.get(key)
    }

    if request.method == "POST":
        form = MediaItemForm(request.POST)
        if form.is_valid():
            media_item = form.save(commit=False)
            if request.user.is_authenticated:
                media_item.user = request.user
            media_item.save()
            messages.success(request, f'Added "{media_item.title}" to your media tracker.')
            destination = reverse(_category_route_name(media_item.category))
            if _is_htmx_request(request):
                return JsonResponse({"ok": True}, headers={"HX-Location": destination})
            return redirect(destination)
    else:
        form = MediaItemForm(initial=initial)

    context = {
        "active_page": "media",
        "form": form,
        "page_title": "Add Media",
        "submit_label": "Create",
    }
    return _render_media_page(
        request,
        "media/media_form.html",
        extra_context=context,
        partial_template="media/media_form_partial.html",
        status=400 if request.method == "POST" and form.errors else 200,
    )


@require_http_methods(["GET", "POST"])
def edit_media(request, item_id):
    media_item = get_object_or_404(_base_queryset(request), id=item_id)

    if request.method == "POST":
        form = MediaItemForm(request.POST, instance=media_item)
        if form.is_valid():
            updated_item = form.save()
            messages.success(request, f'Updated "{updated_item.title}".')
            destination = reverse(_category_route_name(updated_item.category))
            if _is_htmx_request(request):
                return JsonResponse({"ok": True}, headers={"HX-Location": destination})
            return redirect(destination)
    else:
        form = MediaItemForm(instance=media_item)

    context = {
        "active_page": "media",
        "form": form,
        "media_item": media_item,
        "page_title": "Edit Media",
        "submit_label": "Save changes",
    }
    return _render_media_page(
        request,
        "media/media_form.html",
        extra_context=context,
        partial_template="media/media_form_partial.html",
        status=400 if request.method == "POST" and form.errors else 200,
    )


@require_http_methods(["GET", "POST"])
def delete_media(request, item_id):
    media_item = get_object_or_404(_base_queryset(request), id=item_id)

    if request.method == "POST":
        route_name = _category_route_name(media_item.category)
        deleted_title = media_item.title
        media_item.delete()
        messages.success(request, f'Deleted "{deleted_title}".')
        destination = reverse(route_name)
        if _is_htmx_request(request):
            return JsonResponse({"ok": True}, headers={"HX-Location": destination})
        return redirect(destination)

    context = {
        "active_page": "media",
        "media_item": media_item,
    }
    return _render_media_page(
        request,
        "media/media_confirm_delete.html",
        extra_context=context,
        partial_template="media/media_confirm_delete_partial.html",
    )


@require_http_methods(["GET", "POST"])
def update_progress(request, item_id):
    media_item = get_object_or_404(_base_queryset(request), id=item_id)
    latest = media_item.latest_progress_entry()

    if request.method == "POST":
        form = MediaProgressForm(request.POST, media_item=media_item)
        if form.is_valid():
            progress = form.save(commit=False)
            progress.media_item = media_item
            progress.save()

            if progress.completed:
                new_status = MediaItem.Status.COMPLETED
            elif (progress.episodes_watched or 0) > 0:
                new_status = MediaItem.Status.WATCHING
            else:
                new_status = media_item.status

            if new_status != media_item.status:
                media_item.status = new_status
                media_item.save(update_fields=["status"])

            messages.success(request, f'Progress updated for "{media_item.title}".')
            destination = reverse(_category_route_name(media_item.category))
            if _is_htmx_request(request):
                return JsonResponse({"ok": True}, headers={"HX-Location": destination})
            return redirect(destination)
    else:
        initial = {}
        if latest:
            initial = {
                "episodes_watched": latest.episodes_watched,
                "current_season": latest.current_season,
                "current_episode": latest.current_episode,
                "date_watched": latest.date_watched,
                "completed": latest.completed,
                "rating": latest.rating,
                "notes": latest.notes,
            }
        form = MediaProgressForm(media_item=media_item, initial=initial)

    context = {
        "active_page": "media",
        "form": form,
        "media_item": media_item,
        "latest_progress": latest,
    }
    return _render_media_page(
        request,
        "media/progress_form.html",
        extra_context=context,
        partial_template="media/progress_form_partial.html",
        status=400 if request.method == "POST" and form.errors else 200,
    )


@require_GET
def api_media_stats(request):
    queryset = _apply_filters(_base_queryset(request), request)
    items = list(queryset.prefetch_related(PROGRESS_PREFETCH))

    payload = {
        "completion_rate": calculate_completion_rate(items),
        "genre_distribution": _genre_distribution(items),
        "watch_time": calculate_watch_time(items),
        "episodes_per_month": _episodes_per_month(MediaProgress.objects.filter(media_item__in=queryset)),
        "global": global_media_analytics(),
    }
    return JsonResponse(payload)


@require_GET
def api_media_movies(request):
    analytics = movies_analytics()
    payload = {
        "completion_rate": analytics.get("completion_rate", 0.0),
        "genre_distribution": analytics.get("genre_distribution", []),
        "watch_time": analytics.get("watch_time", {"minutes": 0, "hours": 0.0}),
        "episodes_per_month": [
            {"month": row.get("month", ""), "value": int(row.get("count", 0))}
            for row in analytics.get("movies_per_month", [])
        ],
        "movies_watched_count": analytics.get("movies_watched_count", 0),
        "movies_remaining_count": analytics.get("movies_remaining_count", 0),
        "movies_per_month": analytics.get("movies_per_month", []),
    }
    return JsonResponse(payload)


@require_GET
def api_media_series(request):
    analytics = series_analytics()
    payload = {
        "completion_rate": analytics.get("completion_rate", 0.0),
        "genre_distribution": analytics.get("genre_distribution", []),
        "watch_time": analytics.get("watch_time", {"minutes": 0, "hours": 0.0}),
        "episodes_per_month": analytics.get("episodes_watched_per_month", []),
        "series_completed": analytics.get("series_completed", 0),
        "series_in_progress": analytics.get("series_in_progress", 0),
        "average_episodes_per_week": analytics.get("average_episodes_per_week", 0.0),
    }
    return JsonResponse(payload)


@require_GET
def api_media_anime(request):
    analytics = anime_analytics()
    payload = {
        "completion_rate": analytics.get("anime_completion_rate", 0.0),
        "genre_distribution": analytics.get("anime_by_genre", []),
        "watch_time": analytics.get("watch_time", {"minutes": 0, "hours": 0.0}),
        "episodes_per_month": _episodes_per_month(
            MediaProgress.objects.filter(media_item__category=MediaItem.Category.ANIME)
        ),
        "episodes_watched": analytics.get("episodes_watched", 0),
    }
    return JsonResponse(payload)
