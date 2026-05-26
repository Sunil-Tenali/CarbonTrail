"""
Ingestion app - Data import pipeline and validation for CarbonTrail.

This module handles the complete data flow:
1. User uploads CSV file from external system (SAP, utility, travel platform)
2. File is parsed into RawActivityRow records (immutable, exact copy)
3. Validation runs, collecting issues
4. Valid/suspicious rows become ActivityRecord entries
5. Audit trail records all changes for compliance

Key design principle: Raw data is immutable. We preserve the exact input
for debugging and compliance auditing.
"""

import hashlib
from django.conf import settings
from django.db import models
from organizations.models import Tenant


class SourceSystem(models.Model):
    """
    Represents an external system providing emissions data.

    Organizations typically have multiple data sources:
    - SAP ERP: Procurement and facility data
    - Utility companies: Electricity, gas, water usage
    - Travel platforms: Business flight and hotel bookings

    The unique_together constraint ensures each organization can't
    have duplicate sources (same name/type combination).
    """

    SOURCE_TYPES = [
        ("sap", "SAP"),
        ("utility", "Utility Electricity"),
        ("travel", "Corporate Travel"),
    ]

    # Which organization owns this data source
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    # Human-readable source name (e.g., "SAP Production", "Duke Energy")
    name = models.CharField(max_length=255)
    # Category of source
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPES)
    # Optional notes about what this source tracks
    description = models.TextField(blank=True)
    # When this source was registered
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevent duplicate sources per organization
        unique_together = ("tenant", "name", "source_type")

    def __str__(self):
        return f"{self.tenant.name} - {self.name}"


class ImportBatch(models.Model):
    """
    Represents a single file upload containing emissions data.

    When a user uploads "emissions_q1_2024.csv", we create an ImportBatch to:
    - Track the upload metadata (who, when, file name)
    - Monitor processing status (processing → completed → failed)
    - Store validation counts (valid/invalid/suspicious/approved rows)
    - Enable rollback by deleting the batch (cascades to RawActivityRow)

    STATUS_CHOICES:
    - processing: Still being validated, UI shows spinner
    - completed: All rows processed, ready for user review
    - failed: Parsing or validation failed, user must reupload
    """

    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    # Which organization this import belongs to
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    # Which source system provided the data
    source_system = models.ForeignKey(SourceSystem, on_delete=models.CASCADE)

    # Original file name as uploaded by user
    original_filename = models.CharField(max_length=255)
    # Audit trail: who uploaded this file
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    # When the file was uploaded
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Current processing status
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="processing",
    )

    # Validation statistics (updated during processing)
    total_rows = models.PositiveIntegerField(default=0)  # Total rows in file
    valid_rows = models.PositiveIntegerField(default=0)  # Passed all checks
    invalid_rows = models.PositiveIntegerField(default=0)  # Has validation errors
    suspicious_rows = models.PositiveIntegerField(default=0)  # Warnings, needs review
    approved_rows = models.PositiveIntegerField(default=0)  # User approved

    def __str__(self):
        return f"{self.original_filename} - {self.status}"


class RawActivityRow(models.Model):
    """
    A single row of data exactly as received from external system.

    IMMUTABILITY PRINCIPLE: Never modify raw_payload or raw_hash.
    This row represents the ground truth of what was sent to us.

    Benefits:
    - Debugging: "What did the source system actually send?"
    - Compliance: Proof data wasn't tampered with
    - Deduplication: raw_hash enables detecting duplicate uploads

    Relationships:
    - One RawActivityRow → One ActivityRecord (via OneToOneField)
    - The hash enables quick lookup for de-duplication

    Design: Use JSONField for raw_payload to support different
    source schemas (SAP columns differ from utility company columns).
    """

    # Which organization owns this data
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    # Which import batch this row came from
    import_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        related_name="raw_rows",
    )

    # Position in original file (for user debugging)
    row_number = models.PositiveIntegerField()
    # Complete data as received from source
    raw_payload = models.JSONField()
    # SHA256 hash of payload for deduplication
    raw_hash = models.CharField(max_length=64, blank=True)

    # When imported
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure no duplicate rows within same import batch
        unique_together = ("import_batch", "row_number")

    def save(self, *args, **kwargs):
        # Automatically compute hash if not already set
        # Hash enables fast duplicate detection across imports
        if not self.raw_hash:
            raw_text = str(sorted(self.raw_payload.items()))
            self.raw_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Row {self.row_number} from {self.import_batch.original_filename}"