from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Tenant
from .serializers import TenantSerializer


class TenantListCreateView(generics.ListCreateAPIView):
    """
    List and create client organizations.

    This is intentionally small for the prototype. It lets the frontend create
    a company/tenant before uploading SAP, utility, or travel CSV files.
    """

    queryset = Tenant.objects.all().order_by("name")
    serializer_class = TenantSerializer
    permission_classes = [AllowAny]