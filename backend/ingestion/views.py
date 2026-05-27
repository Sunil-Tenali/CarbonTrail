"""
API endpoints for data ingestion pipeline.

Handles:
- SourceSystemListView: GET /api/ingestion/source-systems/ - List connected data sources
- ImportBatchListView: GET /api/ingestion/import-batches/ - Track import sessions
- SAPCSVUploadView: POST /api/ingestion/sap/upload/ - Upload and process SAP CSV files
"""

from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.models import Tenant

from .models import ImportBatch, SourceSystem
from .serializers import ImportBatchSerializer, SourceSystemSerializer
from .services.sap_csv_importer import SAPCSVImporter


class SourceSystemListView(generics.ListAPIView):
    """
    List external data sources (SAP, utilities, travel platforms).
    
    Filters:
    - tenant_id: Organization (multi-tenancy)
    - source_type: System type (sap, utility, travel)
    """
    serializer_class = SourceSystemSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = SourceSystem.objects.select_related("tenant").order_by(
            "tenant__name",
            "name",
        )

        tenant_id = self.request.query_params.get("tenant_id")
        source_type = self.request.query_params.get("source_type")

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        if source_type:
            queryset = queryset.filter(source_type=source_type)

        return queryset


class ImportBatchListView(generics.ListAPIView):
    """
    List import sessions with processing status and statistics.
    
    Filters:
    - tenant_id: Organization
    - source_type: Data source system
    - status: Processing state (processing, completed, failed)
    """
    serializer_class = ImportBatchSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = ImportBatch.objects.select_related(
            "tenant",
            "source_system",
            "uploaded_by",
        ).order_by("-uploaded_at")

        tenant_id = self.request.query_params.get("tenant_id")
        source_type = self.request.query_params.get("source_type")
        status_filter = self.request.query_params.get("status")

        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        if source_type:
            queryset = queryset.filter(source_system__source_type=source_type)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset


class SAPCSVUploadView(APIView):
    """
    Upload and process SAP CSV file containing emissions data.
    
    Flow:
    1. Validate file and tenant ID
    2. Create/find SourceSystem for tenant
    3. Parse CSV using SAPCSVImporter service
    4. Create RawActivityRow records (immutable source copy)
    5. Run validation rules
    6. Create ActivityRecord with initial status
    7. Return ImportBatch with statistics
    
    Response codes:
    - 201: Upload successful (batch created)
    - 400: Invalid input (no file, no tenant, or processing failed)
    - 404: Tenant not found
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        tenant_id = request.data.get("tenant_id")

        if uploaded_file is None:
            return Response(
                {"detail": "Please upload a CSV file using the 'file' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if tenant_id is None:
            return Response(
                {"detail": "Please provide tenant_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response(
                {"detail": "Tenant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get or create SAP data source for this organization
        source_system, _created = SourceSystem.objects.get_or_create(
            tenant=tenant,
            name="SAP Fuel CSV Upload",
            source_type="sap",
            defaults={
                "description": (
                    "Prototype SAP CSV ingestion for fuel and procurement rows."
                )
            },
        )

        # Capture current user if authenticated
        uploaded_by = request.user if request.user.is_authenticated else None

        # Delegate CSV processing to service layer
        importer = SAPCSVImporter(
            tenant=tenant,
            source_system=source_system,
            uploaded_by=uploaded_by,
        )

        # Import returns ImportBatch with status and validation statistics
        batch = importer.import_file(uploaded_file)

        serializer = ImportBatchSerializer(batch)

        # Return error status if processing failed
        if batch.status == "failed":
            return Response(
                serializer.data,
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )