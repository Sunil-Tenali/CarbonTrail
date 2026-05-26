import hashlib
from django.conf import settings
from django.db import models
from organizations.models import Tenant


class SourceSystem(models.Model):
    SOURCE_TYPES = [
        ("sap", "SAP"),
        ("utility", "Utility Electricity"),
        ("travel", "Corporate Travel"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "name", "source_type")

    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class ImportBatch(models.Model):
    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    source_system = models.ForeignKey(SourceSystem, on_delete=models.CASCADE)

    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="processing",
    )

    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    suspicious_rows = models.PositiveIntegerField(default=0)
    approved_rows = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.original_filename} - {self.status}"


class RawActivityRow(models.Model):
    """
    Original row exactly as received from CSV.

    This should not be edited.
    """

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    import_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        related_name="raw_rows",
    )

    row_number = models.PositiveIntegerField()
    raw_payload = models.JSONField()
    raw_hash = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("import_batch", "row_number")

    def save(self, *args, **kwargs):
        if not self.raw_hash:
            raw_text = str(sorted(self.raw_payload.items()))
            self.raw_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Row {self.row_number} from {self.import_batch.original_filename}"