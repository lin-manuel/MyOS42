from django.contrib import admin

from .models import EducationDocument, EducationRecord, Scholarship


@admin.register(EducationRecord)
class EducationRecordAdmin(admin.ModelAdmin):
    list_display = ("level", "institution", "user", "start_year", "end_year", "study_hours")
    search_fields = ("level", "institution", "user__email")


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "status", "deadline", "user")
    list_filter = ("status", "country")
    search_fields = ("name", "user__email")


@admin.register(EducationDocument)
class EducationDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "document_type", "version", "expires_at", "user")
    list_filter = ("document_type",)
    search_fields = ("title", "user__email")
