"""
Admin interface for activities app.

Provides tools for CarbonTrail staff to:
- View and filter emissions activity records
- Monitor approval status and workflow
- Review validation issues detected during import
- Inspect approved activities for reports
"""

from django.contrib import admin
from .models import ActivityRecord, ValidationIssue


@admin.register(ActivityRecord)
class ActivityRecordAdmin(admin.ModelAdmin):
    """
    Displays list view with key fields for understanding data state:
    - tenant: Which organization
    - source_type: Where data came from (SAP, utility, travel)
    - activity_type: Type of emission (fuel, electricity, flight, etc.)
    - scope: GHG Protocol scope (1, 2, 3)
    - status: Approval state (valid, suspicious, invalid, approved, rejected)
    - is_locked: Whether record is locked (immutable)
    - approved_at: When user approved
    """
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
    """
    Admin interface for validation issues found during import.

    Issues are either:
    - error: Critical problem (invalid format, missing required data)
    - warning: Worth noting but usable (outliers, optional fields missing)

    Helps staff understand why data was flagged as "suspicious" or "invalid".
    """
    list_display = ("id", "tenant", "activity_record", "severity", "code", "created_at")
    list_filter = ("severity", "code")