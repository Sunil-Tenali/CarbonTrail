"""
Serializers for ActivityRecord API responses.

Serializers convert Python objects to/from JSON for REST API:
- Convert ActivityRecord models to JSON responses
- Validate input data from clients
- Hide sensitive fields (if needed)
- Denormalize related data (tenant_name, issue_count)
"""

from rest_framework import serializers

from .models import ActivityRecord, ValidationIssue


class ValidationIssueSerializer(serializers.ModelSerializer):
    """
    Serializes a ValidationIssue - a problem found during import validation.

    Used when returning ActivityRecord details - includes all validation
    errors/warnings found with that record so client knows why it's
    flagged as invalid or suspicious.

    FIELDS:
    - id: Issue identifier
    - severity: "error" (critical) or "warning" (informational)
    - code: Machine-readable code (MISSING_FACILITY_ID, OUTLIER_QUANTITY)
    - message: Human-readable explanation
    - created_at: When detected
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
    Main serializer for ActivityRecord REST API responses.

    NESTED FIELDS:
    - issues: List of ValidationIssue objects (read-only)
    - tenant_name: Organization name (denormalized from tenant.name)
    - issue_count: Total validation issues found

    READ-ONLY FIELDS:
    These are set by system, not client:
    - status: Set by approval workflow
    - is_locked: Set by approve() action
    - approved_by: Set by approve() action
    - approved_at: Set by approve() action
    - locked_at: Set by approve() action
    - created_at: Set on creation
    - updated_at: Set on modification

    EDITABLE FIELDS:
    Client can update these (if record not locked):
    - source_type: Where data came from
    - activity_type: Type of emission
    - scope: GHG Protocol scope (1/2/3)
    - facility_code: Organizational location
    - cost_center: Financial allocation
    - activity_date: Single date or...
    - period_start/period_end: ...date range
    - quantity_original/unit_original: Original as received
    - quantity_normalized/unit_normalized: Standardized for calculations
    - amount: Financial value
    - currency: Currency code
    - source_reference: External tracking ID
    """

    # Embed full validation issue details
    issues = ValidationIssueSerializer(many=True, read_only=True)
    # Denormalize tenant name (avoids client making extra request)
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    # Calculate issue count for easy dashboard display
    issue_count = serializers.SerializerMethodField()

    class Meta:
        model = ActivityRecord
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
        ]

        # Fields that API should never allow client to modify
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