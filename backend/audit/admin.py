"""
Admin interface for audit app.

Provides tools for CarbonTrail staff and compliance officers to:
- View all user actions and changes
- Track who did what and when
- Audit emissions data changes
- Investigate data modifications
- Generate compliance reports
"""

from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for audit trail.

    Displays all tracked actions with:
    - id: Record identifier
    - tenant: Which organization
    - action: Type of action (approved, deleted, updated, etc.)
    - entity_type: What was changed (ActivityRecord, ImportBatch)
    - entity_id: Which record
    - created_at: When the action occurred

    Filters help find:
    - Actions by type (all approvals, deletions, etc.)
    - Changes by entity type
    - User activity patterns
    """
    list_display = ("id", "tenant", "action", "entity_type", "entity_id", "created_at")
    list_filter = ("action", "entity_type")