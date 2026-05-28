"""
Serializers for ActivityRecord API responses.
"""

from rest_framework import serializers

from .models import ActivityRecord, ValidationIssue


class ValidationIssueSerializer(serializers.ModelSerializer):
    """
    Validation problem found during CSV import.

    Severity is "error" (blocks activity) or "warning" (flag for review).
    Code is machine-readable (e.g., MISSING_METER_ID) for client filtering.
    """
    class Meta:
        model = ValidationIssue
        fields = [
            "id",
            "severity",
            "code",
            "message",
            "created_at",
        ]


class ActivityRecordSerializer(serializers.ModelSerializer):
    """
    REST API response format for activity records.

    Includes validation issues, tenant name, and raw CSV payload for audit
    trail. The raw_payload field preserves the original CSV row so analysts
    can verify exact source data during review.

    Read-only fields (status, approval state, timestamps) are set only by
    system operations like approve() or reject() to maintain audit integrity.
    """

    # Nested validation issues for analyst review
    issues = ValidationIssueSerializer(many=True, read_only=True)
    # Denormalize tenant name to avoid extra API call
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    # Count total issues for dashboard display
    issue_count = serializers.SerializerMethodField()
    # Preserve original CSV row for audit trail: analysts can verify source data
    raw_payload = serializers.JSONField(source="raw_row.raw_payload", read_only=True)
    raw_row_number = serializers.IntegerField(source="raw_row.row_number", read_only=True)
    import_batch_id = serializers.IntegerField(
        source="raw_row.import_batch_id",
        read_only=True,
    )

    class Meta:
        model = ActivityRecord
        # Fields are grouped by concern: identity, org, classification, timing, quantities, financials, traceability, workflow, validation, lifecycle
        fields = [
            # Identity
            "id",

            # Organization (multi-tenancy)
            "tenant",
            "tenant_name",

            # Classification
            "source_type",
            "activity_type",
            "scope",

            # Organizational tracking
            "facility_code",
            "cost_center",

            # Timing
            "activity_date",
            "period_start",
            "period_end",

            # Quantity & units
            "quantity_original",
            "unit_original",
            "quantity_normalized",
            "unit_normalized",

            # Financial
            "amount",
            "currency",

            # Traceability
            "source_reference",

            # Workflow state
            "status",
            "is_locked",
            "approved_by",
            "approved_at",
            "locked_at",

            # Validation results
            "issue_count",
            "issues",

            # Lifecycle
            "created_at",
            "updated_at",
            "raw_payload",
            "raw_row_number",
            "import_batch_id",
        ]

        # These fields are set only by approve()/reject() actions to maintain audit trail
        read_only_fields = [
            "status",
            "is_locked",
            "approved_by",
            "approved_at",
            "locked_at",
            "created_at",
            "updated_at",
        ]

    def get_issue_count(self, obj):
        """Count total validation issues for display purposes"""
        return obj.issues.count()