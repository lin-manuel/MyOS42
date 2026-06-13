from django.contrib import admin

from .models import Project, ProjectAttachment, ProjectNote, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "priority", "progress", "start_date", "deadline", "is_archived")
    list_filter = ("status", "priority")
    search_fields = ("title", "description", "user__email")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "priority", "due_date", "completed_at")
    list_filter = ("status", "priority")
    search_fields = ("title", "description", "project__title", "project__user__email")


@admin.register(ProjectNote)
class ProjectNoteAdmin(admin.ModelAdmin):
    list_display = ("project", "created_at")
    search_fields = ("project__title", "content")


@admin.register(ProjectAttachment)
class ProjectAttachmentAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "user", "created_at")
    search_fields = ("title", "notes", "project__title", "user__email")
