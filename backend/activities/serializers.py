"""
Serializers for ActivityRecord API responses.
"""

from rest_framework import serializers

from .models import ActivityRecord, ValidationIssue


class ValidationIssueSerializer(serializers.ModelSerializer):
    """
    Validation problem found during CSV import.

    Severity is "error" when the row has a real data problem and "warning"
    when the row can still be reviewed but should get analyst attention.
    Code is machine-readable so the frontend can filter or group issues.
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
    REST API response for normalized activity records.

    Includes normalized fields, validation issues, and raw payload.
    Raw source data is exposed so reviewers can compare original row
    with the normalized ActivityRecord.
    """

    # Keep issues nested so the review screen can show problems beside the row.
    issues = ValidationIssueSerializer(many=True, read_only=True)

    # Small denormalized fields make the frontend easier without changing models.
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    issue_count = serializers.SerializerMethodField()

    # Raw source evidence is exposed for row detail and audit review.
    raw_payload = serializers.JSONField(source="raw_row.raw_payload", read_only=True)
    raw_row_number = serializers.IntegerField(source="raw_row.row_number", read_only=True)
    import_batch_id = serializers.IntegerField(
        source="raw_row.import_batch_id",
        read_only=True,
    )

    class Meta:
        model = ActivityRecord
        fields = [
            # Identity
            "id",

            # Multi-tenancy
            "tenant",
            "tenant_name",

            # Raw row link and source evidence
            "raw_row",
            "raw_payload",
            "raw_row_number",
            "import_batch_id",

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

            # Quantity and unit normalization
            "quantity_original",
            "unit_original",
            "quantity_normalized",
            "unit_normalized",

            # Financial context, if the source provides it
            "amount",
            "currency",

            # Source-of-truth reference, such as meter ID, SAP document, or trip ID
            "source_reference",

            # Analyst workflow and audit lock
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
        ]

        read_only_fields = [
            "id",
            "tenant_name",
            "raw_payload",
            "raw_row_number",
            "import_batch_id",
            "status",
            "is_locked",
            "approved_by",
            "approved_at",
            "locked_at",
            "issue_count",
            "issues",
            "created_at",
            "updated_at",
        ]

    def get_issue_count(self, obj):
        """Count validation issues without making the frontend calculate it."""
        return obj.issues.count()