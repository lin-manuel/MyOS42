from django.db import connection
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

from apps.api.services.dashboard_service import DashboardService
from apps.diary.models import DiaryEntry
from apps.education.models import EducationRecord, Scholarship
from apps.finance.models import FinanceEntry
from apps.media.models import MediaItem
from apps.projects.models import Project, ProjectAttachment, Task
from apps.users.serializers import UserSerializer

DECRYPTED_SCAN_LIMIT = 300
SEARCH_RESULT_LIMIT = 10


class GlobalSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"results": {"projects": [], "diary": [], "finance": [], "media": []}})
        normalized_query = query.lower()

        project_queryset = Project.objects.filter(user=request.user)
        if connection.vendor == "postgresql":
            project_queryset = project_queryset.annotate(
                rank=SearchRank(SearchVector("title", "description"), SearchQuery(query))
            ).filter(rank__gt=0).order_by("-rank")
            projects = list(project_queryset.values("id", "title", "status", "progress")[:SEARCH_RESULT_LIMIT])
        else:
            projects = list(
                project_queryset.filter(Q(title__icontains=query) | Q(description__icontains=query)).values(
                    "id", "title", "status", "progress"
                )[:SEARCH_RESULT_LIMIT]
            )
        diary = []
        for entry in DiaryEntry.objects.filter(user=request.user).order_by("-date", "-created_at")[:DECRYPTED_SCAN_LIMIT]:
            content = (entry.content or "").lower()
            mood = (entry.mood or "").lower()
            title = (entry.title or "").lower()
            if normalized_query in content or normalized_query in mood or normalized_query in title:
                diary.append({"id": entry.id, "title": entry.title, "date": entry.date, "mood": entry.mood})
            if len(diary) >= SEARCH_RESULT_LIMIT:
                break

        finance = []
        for entry in FinanceEntry.objects.filter(user=request.user).order_by("-date", "-created_at")[:DECRYPTED_SCAN_LIMIT]:
            category = (entry.category or "").lower()
            description = (entry.description or "").lower()
            account = (entry.account or "").lower()
            if normalized_query in category or normalized_query in description or normalized_query in account:
                finance.append(
                    {"id": entry.id, "type": entry.type, "amount": entry.amount, "account": entry.account, "date": entry.date}
                )
            if len(finance) >= SEARCH_RESULT_LIMIT:
                break

        media = list(
            MediaItem.objects.filter(user=request.user)
            .filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(genre__icontains=query)
                | Q(studio__icontains=query)
            )
            .values("id", "title", "type", "category", "status")[:SEARCH_RESULT_LIMIT]
        )

        education = list(
            Scholarship.objects.filter(user=request.user)
            .filter(Q(name__icontains=query) | Q(country__icontains=query) | Q(notes__icontains=query))
            .values("id", "name", "country", "status", "deadline")[:SEARCH_RESULT_LIMIT]
        )
        education += list(
            EducationRecord.objects.filter(user=request.user)
            .filter(Q(level__icontains=query) | Q(institution__icontains=query))
            .values("id", "level", "institution", "start_year", "end_year")[:SEARCH_RESULT_LIMIT]
        )
        tasks = list(
            Task.objects.filter(project__user=request.user)
            .filter(Q(title__icontains=query) | Q(description__icontains=query))
            .values("id", "title", "status", "project_id")[:SEARCH_RESULT_LIMIT]
        )

        return Response(
            {
                "results": {
                    "projects": projects,
                    "tasks": tasks,
                    "diary": diary,
                    "finance": finance,
                    "media": media,
                    "education": education,
                }
            }
        )


class DashboardAggregationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = DashboardService.get_dashboard_payload(request.user)
        return Response(payload)


class AccountExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = {
            "user": UserSerializer(request.user).data,
            "projects": list(Project.objects.filter(user=request.user).values()),
            "tasks": list(Task.objects.filter(project__user=request.user).values()),
            "project_attachments": list(ProjectAttachment.objects.filter(user=request.user).values()),
            "finance": list(FinanceEntry.objects.filter(user=request.user).values()),
            "diary": list(DiaryEntry.objects.filter(user=request.user).values()),
            "media": list(MediaItem.objects.filter(user=request.user).values()),
            "education_records": list(EducationRecord.objects.filter(user=request.user).values()),
            "scholarships": list(Scholarship.objects.filter(user=request.user).values()),
        }
        return Response(payload)
