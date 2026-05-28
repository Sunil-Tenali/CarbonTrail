from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = AuditLog.objects.select_related(
            "tenant",
            "actor",
        ).order_by("-created_at")

        tenant_id = self.request.query_params.get("tenant_id")
        entity_type = self.request.query_params.get("entity_type")
        entity_id = self.request.query_params.get("entity_id")
        action = self.request.query_params.get("action")

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)

        if action:
            queryset = queryset.filter(action=action)

        return queryset