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
    """Create point-in-time snapshot for audit logging before/after changes."""
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
    REST API for emissions activity records.

    Endpoints: list, retrieve, update, approve, reject, summary.
    Locked records prevent further edits to enforce compliance immutability.
    """

    serializer_class = ActivityRecordSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        List activity records with optional filters.
        Uses select_related and prefetch_related for query efficiency.
        """
        queryset = (
            ActivityRecord.objects
            .select_related("tenant", "raw_row")
            .prefetch_related("issues")
            .order_by("-created_at")
        )

        tenant_id = self.request.query_params.get("tenant_id")
        status_filter = self.request.query_params.get("status")
        source_type = self.request.query_params.get("source_type")
        
        scope = self.request.query_params.get("scope")
        activity_type = self.request.query_params.get("activity_type")
        batch_id = self.request.query_params.get("batch_id")
        validation_state = self.request.query_params.get("validation_state")

        if scope:
            queryset = queryset.filter(scope=scope)

        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)

        if batch_id:
            queryset = queryset.filter(raw_row__import_batch_id=batch_id)

        if validation_state == "has_issues":
            queryset = queryset.filter(issues__isnull=False).distinct()

        if validation_state == "no_issues":
            queryset = queryset.filter(issues__isnull=True)

        if validation_state == "errors":
            queryset = queryset.filter(issues__severity="error").distinct()

        if validation_state == "warnings":
            queryset = queryset.filter(issues__severity="warning").distinct()

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if source_type:
            queryset = queryset.filter(source_type=source_type)

        return queryset

    def update(self, request, *args, **kwargs):
        """
        Update an activity record (PUT).
        Locked records cannot be edited to enforce compliance immutability.
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
        Get approval statistics (total, valid, suspicious, invalid, approved, rejected).
        Respects all filters from list endpoint (tenant_id, status, source_type, etc.).
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
        Approve a record for use in reports and lock it for audit immutability.
        Only valid/suspicious unlocked records can be approved.
        """
        record = self.get_object()

        if not record.can_be_approved():
            return Response(
                {
                    "detail": (
                        "Only valid or suspicious unlocked records can be approved."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user if request.user.is_authenticated else None
        before_snapshot = build_activity_snapshot(record)
        now = timezone.now()

        with transaction.atomic():
            record.status = "approved"
            record.approved_by = user
            record.approved_at = now
            record.is_locked = True
            record.locked_at = now

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

            after_snapshot = build_activity_snapshot(record)

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

        serializer = self.get_serializer(record)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """
        Reject an activity record as unusable (unlock so analyst can resubmit).

        Preconditions: Record must not be locked.
        Reasons can be provided in request body as {"reason": "..."}
        """
        record = self.get_object()

        if record.is_locked:
            return Response(
                {"detail": "This activity record is locked and cannot be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user if request.user.is_authenticated else None
        reason = request.data.get("reason", "Rejected during analyst review.")
        before_snapshot = build_activity_snapshot(record)

        with transaction.atomic():
            record.status = "rejected"

            record.save(
                update_fields=[
                    "status",
                    "updated_at",
                ]
            )

            after_snapshot = build_activity_snapshot(record)

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

        serializer = self.get_serializer(record)

        return Response(serializer.data, status=status.HTTP_200_OK)