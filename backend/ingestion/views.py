"""
API endpoints for data ingestion pipeline.

Handles:
- SourceSystemListView: GET /api/ingestion/source-systems/ - List connected data sources
- ImportBatchListView: GET /api/ingestion/import-batches/ - Track import sessions
- CSVUploadView: POST /api/ingestion/upload/ - Route CSV to correct importer
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
from .services.utility_csv_importer import UtilityElectricityCSVImporter
from .services.travel_csv_importer import TravelCSVImporter


class SourceSystemListView(generics.ListAPIView):
    """
    List connected data sources (SAP systems, utility accounts, travel platforms).
    Filters by tenant_id and source_type.
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
    List CSV import sessions with statistics (total, valid, invalid, suspicious rows).
    Filters by tenant_id, source_type, and status.
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


class CSVUploadView(APIView):
    """
    Upload and route CSV file to correct importer based on source_type.

    Request fields:
    - tenant_id: Organization ID
    - source_type: One of 'sap', 'utility', 'travel'
    - file: CSV file to import
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]

    IMPORTERS = {
        "sap": {
            "class": SAPCSVImporter,
            "name": "SAP Fuel and Procurement CSV Upload",
            "description": "SAP flat-file CSV upload for fuel and procurement data.",
        },
        "utility": {
            "class": UtilityElectricityCSVImporter,
            "name": "Utility Electricity CSV Upload",
            "description": "Utility portal CSV upload for electricity billing data.",
        },
        "travel": {
            "class": TravelCSVImporter,
            "name": "Corporate Travel CSV Upload",
            "description": "Corporate travel CSV upload for flights, hotels, and ground transport.",
        },
    }

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        tenant_id = request.data.get("tenant_id")
        source_type = request.data.get("source_type")

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

        if source_type not in self.IMPORTERS:
            return Response(
                {"detail": "source_type must be one of: sap, utility, travel."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response(
                {"detail": "Tenant not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        config = self.IMPORTERS[source_type]

        source_system, _created = SourceSystem.objects.get_or_create(
            tenant=tenant,
            name=config["name"],
            source_type=source_type,
            defaults={"description": config["description"]},
        )

        uploaded_by = request.user if request.user.is_authenticated else None

        importer = config["class"](
            tenant=tenant,
            source_system=source_system,
            uploaded_by=uploaded_by,
        )

        batch = importer.import_file(uploaded_file)
        serializer = ImportBatchSerializer(batch)

        if batch.status == "failed":
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data, status=status.HTTP_201_CREATED)