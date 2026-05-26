from django.contrib import admin
from .models import ActivityRecord, ValidationIssue


@admin.register(ActivityRecord)
class ActivityRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant",
        "source_type",
        "activity_type",
        "scope",
        "status",
        "is_locked",
        "approved_at",
    )
    list_filter = ("source_type", "activity_type", "scope", "status", "is_locked")


@admin.register(ValidationIssue)
class ValidationIssueAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "activity_record", "severity", "code", "created_at")
    list_filter = ("severity", "code")