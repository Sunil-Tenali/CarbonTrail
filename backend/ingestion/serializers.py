"""
Serializers for ingestion API responses (uploads, batches, data sources).
"""

from rest_framework import serializers

from .models import ImportBatch, SourceSystem


class SourceSystemSerializer(serializers.ModelSerializer):
    """
    External data source (SAP, utility company, travel platform).
    Denormalize tenant name for easier filtering and display.
    """
    # Denormalize tenant name to avoid extra API call
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)

    class Meta:
        model = SourceSystem
        fields = [
            "id",
            # Organization context
            "tenant",
            "tenant_name",
            # Source metadata
            "name",
            "source_type",
            "description",
            # Timeline
            "created_at",
        ]


class ImportBatchSerializer(serializers.ModelSerializer):
    """
    Single CSV file upload session with processing statistics.
    
    Denormalized fields expose source system metadata and counts so client
    can display upload progress without extra queries.
    """
    # Denormalize tenant name
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    # Denormalize source system name to display "SAP Production" instead of ID
    source_system_name = serializers.CharField(
        source="source_system.name",
        read_only=True,
    )
    # Denormalize source_type so client knows data source category (sap, utility, travel)
    source_type = serializers.CharField(
        source="source_system.source_type",
        read_only=True,
    )

    class Meta:
        model = ImportBatch
        # Fields grouped by concern: identity, organization, source, file metadata, status, statistics
        fields = [
            "id",
            # Organization context
            "tenant",
            "tenant_name",
            # Source context
            "source_system",
            "source_system_name",
            "source_type",
            # Upload metadata
            "original_filename",
            "uploaded_by",
            "uploaded_at",
            # Processing status
            "status",
            # Row statistics (valid, invalid, suspicious, approved counts)
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "suspicious_rows",
            "approved_rows",
        ]

        # System-managed fields: set during import processing, read-only for client
        read_only_fields = [
            "uploaded_by",
            "uploaded_at",
            "status",
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "suspicious_rows",
            "approved_rows",
        ]