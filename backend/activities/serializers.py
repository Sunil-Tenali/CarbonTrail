from rest_framework import serializers
from .models import ActivityRecord, ValidationIssue


class ValidationIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationIssue
        fields = ["id", "severity", "code", "message", "created_at"]


class ActivityRecordSerializer(serializers.ModelSerializer):
    issues = ValidationIssueSerializer(many=True, read_only=True)

    class Meta:
        model = ActivityRecord
        fields = [
            "id",
            "tenant",
            "source_type",
            "activity_type",
            "scope",
            "facility_code",
            "cost_center",
            "activity_date",
            "period_start",
            "period_end",
            "quantity_original",
            "unit_original",
            "quantity_normalized",
            "unit_normalized",
            "amount",
            "currency",
            "source_reference",
            "status",
            "is_locked",
            "approved_by",
            "approved_at",
            "locked_at",
            "issues",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "is_locked",
            "approved_by",
            "approved_at",
            "locked_at",
            "created_at",
            "updated_at",
        ]