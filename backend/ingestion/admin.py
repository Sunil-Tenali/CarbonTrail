"""
Django Admin interface for the ingestion app.

Provides tools for staff to:
- Monitor data import batches (status, progress, error rates)
- Inspect raw data received from external systems
- Debug parsing and validation issues
- Audit who uploaded what and when

IMPORTANT: In production, only grant admin access to trusted staff.
Consider adding audit logging for all admin actions.
"""

from django.contrib import admin
from .models import SourceSystem, ImportBatch, RawActivityRow


@admin.register(SourceSystem)
class SourceSystemAdmin(admin.ModelAdmin):
    """
    Manage external data sources.

    Allows staff to:
    - Track which systems each organization is connected to
    - Update descriptions when source changes
    - Monitor creation dates for account lifecycle

    FIELDS:
    - id: Database primary key
    - tenant: Which organization owns this source
    - name: Human-friendly name
    - source_type: Category (SAP, utility, travel)
    - created_at: When added to the system

    Filter by source_type to quickly find all SAP systems, utilities, etc.
    """

    list_display = ("id", "tenant", "name", "source_type", "created_at")
    list_filter = ("source_type", "created_at")
    search_fields = ("tenant__name", "name")
    readonly_fields = ("created_at",)
    
    fieldsets = (
        ("System Configuration", {
            "fields": ("tenant", "name", "source_type")
        }),
        ("Details", {
            "fields": ("description",)
        }),
        ("Metadata", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    """
    Monitor data import sessions.

    Key fields for understanding import health:
    - status: Is import still processing, completed, or failed?
    - total_rows: How many rows in this upload
    - valid_rows: Passed validation
    - suspicious_rows: Flagged for manual review
    - invalid_rows: Cannot be used (data quality issues)
    - approved_rows: User approved for use in reports

    EXAMPLE INTERPRETATION:
    If total_rows=100, valid_rows=80, suspicious_rows=10, invalid_rows=10:
    - 80% fully valid data
    - 10% needs human review
    - 10% unusable

    Use list_filter by status to quickly find:
    - "processing": Uploads still being validated
    - "completed": Ready for user review
    - "failed": Need to investigate errors

    AUDIT TRAIL:
    - uploaded_by: Which user uploaded (for audit trail)
    - uploaded_at: When (for tracking data recency)
    - source_system: Where data came from
    """

    list_display = (
        "id",
        "tenant",
        "source_system",
        "original_filename",
        "status",
        "total_rows",
        "valid_rows",
        "invalid_rows",
        "suspicious_rows",
        "approved_rows",
        "uploaded_at",
    )
    list_filter = ("status", "source_system__source_type", "uploaded_at")
    search_fields = ("tenant__name", "original_filename")
    readonly_fields = ("uploaded_at", "total_rows", "valid_rows", "invalid_rows", "suspicious_rows", "approved_rows")
    
    fieldsets = (
        ("Upload Information", {
            "fields": ("tenant", "source_system", "original_filename", "uploaded_by", "uploaded_at")
        }),
        ("Processing Status", {
            "fields": ("status",)
        }),
        ("Validation Results", {
            "fields": ("total_rows", "valid_rows", "invalid_rows", "suspicious_rows", "approved_rows")
        }),
    )

    def has_add_permission(self, request):
        """Prevent manual creation in admin; batches are created via API"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion to rollback failed imports, but with caution"""
        return True


@admin.register(RawActivityRow)
class RawActivityRowAdmin(admin.ModelAdmin):
    """
    View raw imported data.

    IMPORTANT: These are IMMUTABLE records - they should never be edited.
    This is the ground truth of what external systems sent us.

    USE FOR:
    - Debugging: "What did SAP actually send?"
    - Compliance: "Prove we didn't modify the data"
    - De-duplication: Check if row was seen before (raw_hash)

    FIELDS:
    - row_number: Position in original file
    - raw_payload: Complete JSON as received
    - raw_hash: SHA256 hash for deduplication
    - created_at: Import timestamp

    NOTE: raw_payload can be large for files with many columns.
    Use the raw_hash field to detect duplicate rows across imports.

    Usually filtered by import_batch, not viewed directly in bulk.
    """

    list_display = ("id", "tenant", "import_batch", "row_number", "created_at")
    list_filter = ("created_at", "import_batch__source_system__source_type")
    search_fields = ("tenant__name", "import_batch__original_filename")
    readonly_fields = ("raw_hash", "created_at", "raw_payload")
    
    fieldsets = (
        ("Row Information", {
            "fields": ("tenant", "import_batch", "row_number")
        }),
        ("Data", {
            "fields": ("raw_payload",),
            "classes": ("wide", "monospace")
        }),
        ("Integrity", {
            "fields": ("raw_hash",),
            "classes": ("collapse",)
        }),
        ("Metadata", {
            "fields": ("created_at",),
            "classes": ("collapse",)
        }),
    )

    def has_add_permission(self, request):
        """Prevent manual creation; rows created during import"""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent editing; these records are immutable"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion only to rollback imports"""
        return True