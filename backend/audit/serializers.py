"""
Serializers for AuditLog API responses.
"""

from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Audit trail entry showing who did what and when.

    Denormalized fields (actor_email, tenant_name) avoid extra API calls.
    before/after snapshots enable compliance audits to verify data integrity.
    """
    # Denormalize actor email to avoid extra API call for user details
    actor_email = serializers.EmailField(source="actor.email", read_only=True)
    # Denormalize tenant name for easier filtering and display
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)

    class Meta:
        model = AuditLog
        # Fields grouped by concern: identity, actor, what changed, when, snapshots
        fields = [
            "id",
            # Organization context
            "tenant",
            "tenant_name",
            # Who performed action
            "actor",
            "actor_email",
            # What happened
            "action",
            "entity_type",
            "entity_id",
            # Before/after state for compliance verification
            "before",
            "after",
            # Description of action
            "message",
            # Timeline
            "created_at",
        ]
        # All fields are read-only: AuditLog is immutable for compliance
        read_only_fields = fields