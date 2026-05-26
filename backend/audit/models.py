"""
Audit app - Compliance and change tracking for CarbonTrail.

This module implements the audit trail for regulatory compliance and
internal accountability. All significant changes to emissions data are
logged with:
- WHO made the change (actor/user)
- WHAT changed (entity_type and entity_id)
- WHEN it happened (created_at)
- WHAT changed (before/after snapshots as JSON)
- WHY it happened (message/description)

This audit trail enables:
- Compliance reporting: Prove data integrity for carbon audits
- Debugging: Understand what changed and why
- Accountability: Track user actions
- Rollback: Revert problematic changes if needed
"""

from django.conf import settings
from django.db import models
from organizations.models import Tenant


class AuditLog(models.Model):
    """
    A record of a significant action or change in the system.

    Captures what happened, who did it, and when:
    - tenant: Which organization
    - actor: User who performed the action (null if system action)
    - action: Type of action (created, updated, deleted, approved, etc.)
    - entity_type: What was changed (ActivityRecord, ImportBatch, etc.)
    - entity_id: Which specific record was affected
    - before: JSON snapshot of data before change (optional)
    - after: JSON snapshot of data after change (optional)
    - message: Human-readable description
    - created_at: When the action occurred

    EXAMPLE AUDIT LOGS:
    - User approved an ActivityRecord (action=approved)
    - System rejected invalid ImportBatch (action=rejected, actor=null)
    - Admin deleted an old import (action=deleted)
    - User locked a record for compliance period (action=locked)

    For compliance audits, this table proves:
    - Data was not modified after approval
    - All changes were tracked
    - Responsible users are identified
    """

    # Which organization
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    # Who performed the action (null if system action)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    # Type of action performed (created, updated, deleted, approved, rejected, etc.)
    action = models.CharField(max_length=100)
    # What type of entity was affected (ActivityRecord, ImportBatch, etc.)
    entity_type = models.CharField(max_length=100)
    # Which specific record was affected
    entity_id = models.PositiveIntegerField()

    # State before and after (for tracking what changed)
    before = models.JSONField(null=True, blank=True)  # Before state
    after = models.JSONField(null=True, blank=True)   # After state

    # Human-readable description of what happened
    message = models.TextField(blank=True)

    # When the action occurred
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} {self.entity_type} {self.entity_id}"