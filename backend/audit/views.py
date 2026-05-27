"""
Views for audit trail access.

Currently empty - audit logs are managed via Django admin.

AUDIT LOG PURPOSE:
Compliance requirement: Track all significant changes to emissions data
enabling audits to prove integrity and identify responsible users.

EVERY ACTION LOGGED:
- ActivityRecord approved → AuditLog created with before/after
- ActivityRecord rejected → AuditLog created with reason
- ActivityRecord updated → Could log in future
- ImportBatch created → Could log in future
- User actions → Tied to actor (user who performed action)

FUTURE ENDPOINTS (if audit API needed):
GET /api/audit-logs/
    - List all audit entries
    - Filter by:
      * action: "approved", "rejected", "deleted", etc.
      * entity_type: "ActivityRecord", "ImportBatch", etc.
      * actor: Which user performed action
      * date_range: When it happened
    - For compliance officers to review changes

GET /api/audit-logs/{id}/
    - Get detail of single audit event
    - Show before/after snapshots
    - Show who, what, when, why

COMPLIANCE REQUIREMENTS:
- All approved records must have audit trail
- Records cannot be modified after approval (is_locked=True)
- Deletion must be audited
- Immutable record of all changes for carbon audits

CURRENT IMPLEMENTATION:
- ActivityRecordViewSet.approve() creates AuditLog
- ActivityRecordViewSet.reject() creates AuditLog
- Audit trail visible in Django admin for staff

See: audit/models.py (AuditLog model)
See: audit/admin.py (admin interface)
"""
