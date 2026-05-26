from django.contrib import admin
from .models import SourceSystem, ImportBatch, RawActivityRow


@admin.register(SourceSystem)
class SourceSystemAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "name", "source_type", "created_at")
    list_filter = ("source_type",)


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tenant",
        "source_system",
        "original_filename",
        "status",
        "total_rows",
        "valid_rows",
        "invalid_rows",
        "suspicious_rows",
        "approved_rows",
        "uploaded_at",
    )
    list_filter = ("status", "source_system__source_type")


@admin.register(RawActivityRow)
class RawActivityRowAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "import_batch", "row_number", "created_at")