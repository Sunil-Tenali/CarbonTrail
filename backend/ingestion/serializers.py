"""
Serializers for ingestion API responses.
"""

from rest_framework import serializers

from .models import ImportBatch, SourceSystem


class SourceSystemSerializer(serializers.ModelSerializer):
    """
    External data source such as SAP, utility CSV, or travel platform export.
    """

    tenant_name = serializers.CharField(source="tenant.name", read_only=True)

    class Meta:
        model = SourceSystem
        fields = [
            "id",
            "tenant",
            "tenant_name",
            "name",
            "source_type",
            "description",
            "created_at",
        ]


class ImportBatchSerializer(serializers.ModelSerializer):
    """
    One uploaded CSV file and its processing summary.

    The denormalized tenant/source fields are here so the frontend can show a
    useful batch table without making extra API calls for each row.
    """

    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    source_system_name = serializers.CharField(
        source="source_system.name",
        read_only=True,
    )
    source_type = serializers.CharField(
        source="source_system.source_type",
        read_only=True,
    )

    class Meta:
        model = ImportBatch
        fields = [
            "id",

            "tenant",
            "tenant_name",

            "source_system",
            "source_system_name",
            "source_type",

            "original_filename",
            "uploaded_by",
            "uploaded_at",

            "status",

            "total_rows",
            "valid_rows",
            "invalid_rows",
            "suspicious_rows",
            "approved_rows",
        ]

        read_only_fields = [
            "id",
            "tenant_name",
            "source_system_name",
            "source_type",
            "uploaded_by",
            "uploaded_at",
            "status",
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "suspicious_rows",
            "approved_rows",
        ]