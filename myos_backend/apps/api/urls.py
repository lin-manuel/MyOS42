from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.api.views import AccountExportAPIView, DashboardAggregationAPIView, GlobalSearchAPIView
from apps.bucket.views import BucketCategoryViewSet, BucketItemViewSet
from apps.diary.views import DiaryEntryViewSet
from apps.education.views import EducationDocumentViewSet, EducationRecordViewSet, ScholarshipViewSet
from apps.events.views import AutomationRuleViewSet, EventViewSet
from apps.finance.views import BudgetViewSet, FinanceEntryViewSet, SavingsGoalViewSet
from apps.media.views import EpisodeViewSet, MediaItemViewSet, MediaProgressViewSet, SeasonViewSet
from apps.notifications.views import NotificationViewSet
from apps.projects.views import ProjectAttachmentViewSet, ProjectNoteViewSet, ProjectViewSet, TaskViewSet
from apps.users.views import UserProfileViewSet

router = DefaultRouter()
router.register(r"profile", UserProfileViewSet, basename="profile")
router.register(r"projects", ProjectViewSet, basename="projects")
router.register(r"project-tasks", TaskViewSet, basename="project-tasks")
router.register(r"project-notes", ProjectNoteViewSet, basename="project-notes")
router.register(r"project-attachments", ProjectAttachmentViewSet, basename="project-attachments")
router.register(r"finance", FinanceEntryViewSet, basename="finance")
router.register(r"finance/transactions", FinanceEntryViewSet, basename="finance-transactions")
router.register(r"finance/budgets", BudgetViewSet, basename="finance-budgets")
router.register(r"finance/savings-goals", SavingsGoalViewSet, basename="finance-savings-goals")
router.register(r"education/records", EducationRecordViewSet, basename="education-records")
router.register(r"education/scholarships", ScholarshipViewSet, basename="education-scholarships")
router.register(r"education/documents", EducationDocumentViewSet, basename="education-documents")
router.register(r"diary", DiaryEntryViewSet, basename="diary")
router.register(r"media", MediaItemViewSet, basename="media")
router.register(r"media-progress", MediaProgressViewSet, basename="media-progress")
router.register(r"media-seasons", SeasonViewSet, basename="media-seasons")
router.register(r"media-episodes", EpisodeViewSet, basename="media-episodes")
router.register(r"bucket/categories", BucketCategoryViewSet, basename="bucket-categories")
router.register(r"bucket/items", BucketItemViewSet, basename="bucket-items")
router.register(r"notifications", NotificationViewSet, basename="notifications")
router.register(r"events", EventViewSet, basename="events")
router.register(r"automation-rules", AutomationRuleViewSet, basename="automation-rules")

urlpatterns = [
    path("", include(router.urls)),
    path("", include("apps.users.urls")),
    path("search/", GlobalSearchAPIView.as_view(), name="global_search"),
    path("dashboard/", DashboardAggregationAPIView.as_view(), name="dashboard_aggregation"),
    path("export/account/", AccountExportAPIView.as_view(), name="account_export"),
]
