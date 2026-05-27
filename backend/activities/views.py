from django.db import transaction
from django.utils import timezone

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from audit.models import AuditLog

from .models import ActivityRecord
from .serializers import ActivityRecordSerializer


def build_activity_snapshot(record):
    """
    Create a point-in-time snapshot of record state for audit logging.

    Snapshots capture the complete state before and after changes,
    enabling compliance audits to prove data integrity.

    This snapshot is stored in AuditLog.before and AuditLog.after fields
    as JSON for comparison and debugging.
    """
    return {
        "id": record.id,
        "status": record.status,
        "is_locked": record.is_locked,
        "approved_by_id": record.approved_by_id,
        "approved_at": record.approved_at.isoformat() if record.approved_at else None,
        "locked_at": record.locked_at.isoformat() if record.locked_at else None,
        "quantity_normalized": str(record.quantity_normalized)
        if record.quantity_normalized is not None
        else None,
        "unit_normalized": record.unit_normalized,
    }


class ActivityRecordViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    REST API viewset for emissions activity records.

    Provides endpoints for:
    - Listing: Filter by tenant, status, source_type
    - Retrieving: Get single record with validation issues
    - Updating: Edit unlocked records (quantity, dates, classifications)
    - Approving: Mark valid/suspicious records as approved and lock
    - Rejecting: Mark records as rejected
    - Summarizing: Get approval statistics

    WORKFLOW:
    1. Import creates ActivityRecord + ValidationIssue(s)
    2. Record status = "valid" or "suspicious" or "invalid"
    3. If locked, prevent further edits (compliance)
    4. Analyst reviews and calls approve() or reject()
    5. Approval creates AuditLog entry
    6. Record locked to prevent modification

    PERMISSIONS:
    Currently AllowAny for development. In production, add authentication
    and restrict to organization members only.
    """

    serializer_class = ActivityRecordSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Get filtered list of activity records.

        OPTIMIZATION:
        - select_related("tenant", "raw_row"): Join tables to avoid N+1 queries
        - prefetch_related("issues"): Load validation issues efficiently
        - order_by("-created_at"): Newest first

        FILTERS:
        - tenant_id: Only records for this organization
        - status: Filter by approval state (valid, suspicious, invalid, approved, rejected)
        - source_type: Filter by data source (sap, utility, travel)

        EXAMPLE:
        GET /api/activity-records/?tenant_id=1&status=valid&source_type=sap
        Returns: Valid SAP records for organization 1
        """
        queryset = (
            ActivityRecord.objects
            .select_related("tenant", "raw_row")
            .prefetch_related("issues")
            .order_by("-created_at")
        )

        # Multi-tenancy: Only records for specific organization
        tenant_id = self.request.query_params.get("tenant_id")
        # Filter by approval status
        status_filter = self.request.query_params.get("status")
        # Filter by data source
        source_type = self.request.query_params.get("source_type")

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if source_type:
            queryset = queryset.filter(source_type=source_type)

        return queryset

    def update(self, request, *args, **kwargs):
        """
        Update an entire activity record (PUT).

        Checks if record is locked before allowing edits.
        Locked records cannot be modified (compliance protection).

        VALID UPDATES:
        - quantity_original, unit_original: User correction of original data
        - facility_code, cost_center: Organizational classification
        - activity_date or period_start/end: Timing information

        PREVENTED EDITS:
        - status: Only changeable via approve/reject actions
        - approved_by, approved_at: Set only by approve() action
        - is_locked, locked_at: Set only by approve() action
        """
        record = self.get_object()

        if record.is_locked:
            return Response(
                {"detail": "This activity record is locked and cannot be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """
        Update specific fields of an activity record (PATCH).

        Same locking checks as update() but allows partial changes.

        EXAMPLE:
        PATCH /api/activity-records/123/
        {"facility_code": "WAREHOUSE_A", "cost_center": "CC_2024"}

        Updates only these fields, leaves others unchanged.
        """
        record = self.get_object()

        if record.is_locked:
            return Response(
                {"detail": "This activity record is locked and cannot be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().partial_update(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """
        Get approval statistics across all records.

        Returns count of records in each status:
        - total: All records
        - valid: Passed validation
        - suspicious: Warnings but usable
        - invalid: Has critical errors
        - approved: User approved and locked
        - rejected: User rejected

        EXAMPLE RESPONSE:
        {
            "total": 150,
            "valid": 120,
            "suspicious": 20,
            "invalid": 5,
            "approved": 100,
            "rejected": 10
        }

        USEFUL FOR:
        - Dashboard showing import health
        - Progress tracking during review
        - Identifying problematic batches

        Respects tenant_id, status, source_type filters from get_queryset()
        """
        queryset = self.get_queryset()

        data = {
            "total": queryset.count(),
            "valid": queryset.filter(status="valid").count(),
            "suspicious": queryset.filter(status="suspicious").count(),
            "invalid": queryset.filter(status="invalid").count(),
            "approved": queryset.filter(status="approved").count(),
            "rejected": queryset.filter(status="rejected").count(),
        }

        return Response(data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Approve an activity record for use in reports.

        PRECONDITIONS:
        - Record must be "valid" or "suspicious" (not "invalid")
        - Record must NOT already be locked (prevents double-approving)

        ACTIONS:
        1. Record status → "approved"
        2. Record is_locked → True (prevent further edits)
        3. Capture who approved (approved_by = current user)
        4. Capture when (approved_at, locked_at timestamps)
        5. Create AuditLog entry with before/after snapshots

        DATABASE TRANSACTION:
        Uses transaction.atomic() to ensure consistency:
        - If AuditLog creation fails, approval is rolled back
        - Prevents orphaned audit records

        AUDIT TRAIL:
        Records the complete state change in AuditLog:
        - before: Record state before approval
        - after: Record state after approval (locked=True)
        - message: "Activity record approved and locked for audit."

        RESPONSE:
        Returns updated record with new status and approval metadata.

        EXAMPLE:
        POST /api/activity-records/123/approve/
        Response: {"id": 123, "status": "approved", "is_locked": true, ...}
        """
        record = self.get_object()

        # Validation: Can only approve valid/suspicious unlocked records
        if not record.can_be_approved():
            return Response(
                {
                    "detail": (
                        "Only valid or suspicious unlocked records can be approved."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Capture current user (may be None if unauthenticated)
        user = request.user if request.user.is_authenticated else None
        # Snapshot of record before changes (for audit)
        before_snapshot = build_activity_snapshot(record)
        # Current time for all timestamp fields
        now = timezone.now()

        # Atomic transaction: Either all succeeds or all rolls back
        with transaction.atomic():
            # Update record to approved state
            record.status = "approved"
            record.approved_by = user
            record.approved_at = now
            record.is_locked = True
            record.locked_at = now

            # Save only modified fields (efficient, avoids race conditions)
            record.save(
                update_fields=[
                    "status",
                    "approved_by",
                    "approved_at",
                    "is_locked",
                    "locked_at",
                    "updated_at",
                ]
            )

            # Capture record state after changes
            after_snapshot = build_activity_snapshot(record)

            # Create audit log entry for compliance
            AuditLog.objects.create(
                tenant=record.tenant,
                actor=user,
                action="approved",
                entity_type="ActivityRecord",
                entity_id=record.id,
                before=before_snapshot,
                after=after_snapshot,
                message="Activity record approved and locked for audit.",
            )

        # Return updated record to client
        serializer = self.get_serializer(record)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """
        Reject an activity record (not usable for reports).

        PRECONDITIONS:
        - Record must NOT be locked (cannot reject approved records)
        - Can reject any status: valid, suspicious, or invalid

        ACTIONS:
        1. Record status → "rejected"
        2. DO NOT lock (allows resubmission if user changes mind)
        3. Create AuditLog entry with reason

        AUDIT TRAIL:
        Records the rejection with optional reason:
        - reason: "Rejected during analyst review." (default)
        - Can be overridden by request.data["reason"]

        DATABASE TRANSACTION:
        Uses transaction.atomic() for consistency (same as approve()).

        RESPONSE:
        Returns updated record with status="rejected".

        EXAMPLE:
        POST /api/activity-records/123/reject/
        {
            "reason": "Facility code does not match company records"
        }

        Response: {"id": 123, "status": "rejected", "is_locked": false, ...}
        """
        record = self.get_object()

        # Validation: Cannot reject already-approved (locked) records
        if record.is_locked:
            return Response(
                {"detail": "This activity record is locked and cannot be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Capture current user
        user = request.user if request.user.is_authenticated else None
        # Get optional rejection reason from request payload
        reason = request.data.get("reason", "Rejected during analyst review.")
        # Snapshot before changes
        before_snapshot = build_activity_snapshot(record)

        # Atomic transaction
        with transaction.atomic():
            # Update record to rejected state
            record.status = "rejected"

            # Save updated status
            record.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            # Snapshot after changes
            after_snapshot = build_activity_snapshot(record)

            # Create audit log with rejection reason
            AuditLog.objects.create(
                tenant=record.tenant,
                actor=user,
                action="rejected",
                entity_type="ActivityRecord",
                entity_id=record.id,
                before=before_snapshot,
                after=after_snapshot,
                message=reason,
            )

        # Return updated record to client
        serializer = self.get_serializer(record)

        return Response(serializer.data, status=status.HTTP_200_OK)