from django.contrib import admin
from .models import BucketCategory, BucketItem


@admin.register(BucketCategory)
class BucketCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "color", "item_count", "completed_count", "user", "created_at")
    search_fields = ("name", "user__email")


@admin.register(BucketItem)
class BucketItemAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "starred", "status", "target_date", "completed_at", "created_at")
    list_filter = ("status", "starred", "category")
    search_fields = ("title", "description", "category__name", "user__email")
