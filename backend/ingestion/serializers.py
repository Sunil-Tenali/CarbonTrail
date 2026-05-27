from rest_framework import serializers

from .models import ImportBatch, SourceSystem


class SourceSystemSerializer(serializers.ModelSerializer):
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
            "uploaded_by",
            "uploaded_at",
            "status",
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "suspicious_rows",
            "approved_rows",
        ]