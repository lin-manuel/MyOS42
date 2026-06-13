from django.contrib import admin

from .models import (
    AcademicLevel,
    ApplicationDocument,
    ApplicationCost,
    Budget,
    BucketGoal,
    Category,
    DiaryEntry,
    ExamCertification,
    FinanceAlert,
    IdentityDocuments,
    IdentityUploadedFile,
    NotificationPreference,
    PageFormData,
    PasswordReferences,
    PersonalIdentityVault,
    ContactInfo,
    DigitalAccounts,
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


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "email", "timezone", "updated_at")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("scholarship_deadlines", "task_due_alerts", "diary_prompt", "finance_alerts", "updated_at")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "is_done", "sort_order", "updated_at")
    list_editable = ("is_done", "sort_order")
    ordering = ("sort_order", "id")


@admin.register(DiaryEntry)
class DiaryEntryAdmin(admin.ModelAdmin):
    list_display = ("entry_date", "mood", "created_at")
    ordering = ("-entry_date", "-id")


@admin.register(PageFormData)
class PageFormDataAdmin(admin.ModelAdmin):
    list_display = ("page_slug", "updated_at")
    search_fields = ("page_slug",)


@admin.register(UploadedDocument)
class UploadedDocumentAdmin(admin.ModelAdmin):
    list_display = ("page_slug", "field_key", "original_name", "file_size", "uploaded_at")
    search_fields = ("page_slug", "field_key", "original_name", "label")
    list_filter = ("page_slug", "field_key")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "color", "is_active", "sort_order", "updated_at")
    search_fields = ("name", "slug")
    list_filter = ("kind", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("tx_date", "description", "category", "account", "tx_type", "amount")
    list_filter = ("tx_type", "account", "category")
    search_fields = ("description", "notes")
    date_hierarchy = "tx_date"


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("category", "period_start", "monthly_limit", "warning_threshold_pct", "is_active")
    list_filter = ("is_active", "period_start")


@admin.register(BucketGoal)
class BucketGoalAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "priority", "progress", "target_year", "updated_at")
    list_filter = ("category", "status", "priority")
    search_fields = ("title", "description")


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ("name", "target_amount", "starting_amount", "deadline", "status")
    list_filter = ("status",)
    search_fields = ("name",)


@admin.register(ApplicationCost)
class ApplicationCostAdmin(admin.ModelAdmin):
    list_display = ("item_type", "estimated_cost", "actual_cost", "status", "deadline")
    list_filter = ("item_type", "status")


@admin.register(ProjectBudget)
class ProjectBudgetAdmin(admin.ModelAdmin):
    list_display = ("project_name", "budget_amount", "manual_spent_adjustment", "roi_target_pct", "roi_actual_pct", "status")
    list_filter = ("status",)
    search_fields = ("project_name",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "progress", "start_date", "end_date", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "description")


@admin.register(RecurringExpenseTemplate)
class RecurringExpenseTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "account", "amount", "cadence", "next_due_date", "is_active")
    list_filter = ("cadence", "is_active", "account")


@admin.register(FinanceAlert)
class FinanceAlertAdmin(admin.ModelAdmin):
    list_display = ("alert_type", "severity", "message", "related_model", "related_id", "period_key", "is_read", "created_at")
    list_filter = ("alert_type", "severity", "is_read")
    search_fields = ("message", "related_model", "period_key")


@admin.register(AcademicLevel)
class AcademicLevelAdmin(admin.ModelAdmin):
    list_display = ("level_type", "school_name", "status", "start_year", "end_year", "updated_at")
    list_filter = ("level_type", "status", "certification_exam_completed")
    search_fields = ("school_name", "university_name", "admission_number", "student_number")


@admin.register(ExamCertification)
class ExamCertificationAdmin(admin.ModelAdmin):
    list_display = ("exam_name", "academic_level", "exam_year", "candidate_number", "grade_score", "updated_at")
    list_filter = ("exam_year",)
    search_fields = ("exam_name", "candidate_number", "grade_score", "academic_level__school_name")


@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "document_type", "version", "expiration_date", "updated_at")
    list_filter = ("document_type",)
    search_fields = ("title", "version", "notes")


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "university", "degree_level", "application_deadline", "is_active")
    list_filter = ("country", "degree_level", "is_active")
    search_fields = ("name", "country", "university", "field_of_study")


@admin.register(ScholarshipApplication)
class ScholarshipApplicationAdmin(admin.ModelAdmin):
    list_display = ("scholarship", "status", "is_submitted", "submission_date", "application_id", "updated_at")
    list_filter = ("status", "is_submitted")
    search_fields = ("scholarship__name", "application_id")


@admin.register(ScholarshipRequirement)
class ScholarshipRequirementAdmin(admin.ModelAdmin):
    list_display = ("scholarship", "requirement_name", "is_required", "is_completed", "linked_document", "sort_order")
    list_filter = ("is_required", "is_completed")
    search_fields = ("scholarship__name", "requirement_name")


@admin.register(PersonalIdentityVault)
class PersonalIdentityVaultAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "dob", "gender", "nationality", "updated_at")
    search_fields = ("first_name", "last_name", "nationality")


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ("vault", "primary_email", "primary_phone", "city", "country", "updated_at")
    search_fields = ("primary_email", "primary_phone", "city", "country")


@admin.register(IdentityDocuments)
class IdentityDocumentsAdmin(admin.ModelAdmin):
    list_display = ("vault", "passport_expiry", "updated_at")


@admin.register(IdentityUploadedFile)
class IdentityUploadedFileAdmin(admin.ModelAdmin):
    list_display = ("vault", "file_type", "original_name", "file_size", "updated_at")
    list_filter = ("file_type",)
    search_fields = ("original_name", "vault__first_name", "vault__last_name")


@admin.register(DigitalAccounts)
class DigitalAccountsAdmin(admin.ModelAdmin):
    list_display = ("vault", "platform", "username", "email_used", "updated_at")
    list_filter = ("platform",)
    search_fields = ("username", "email_used", "custom_platform")


@admin.register(SocialProfiles)
class SocialProfilesAdmin(admin.ModelAdmin):
    list_display = ("vault", "linkedin", "twitter_x", "github", "updated_at")


@admin.register(PasswordReferences)
class PasswordReferencesAdmin(admin.ModelAdmin):
    list_display = ("vault", "platform", "username", "email_used", "two_factor_enabled", "password_manager", "updated_at")
    list_filter = ("two_factor_enabled", "password_manager")
    search_fields = ("platform", "username", "email_used", "backup_codes_location")
