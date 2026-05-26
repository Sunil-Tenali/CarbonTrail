from django.conf import settings
from django.db import models
from organizations.models import Tenant
from ingestion.models import RawActivityRow


class ActivityRecord(models.Model):
    SOURCE_TYPES = [
        ("sap", "SAP"),
        ("utility", "Utility"),
        ("travel", "Travel"),
    ]

    ACTIVITY_TYPES = [
        ("fuel", "Fuel"),
        ("procurement", "Procurement"),
        ("electricity", "Electricity"),
        ("flight", "Flight"),
        ("hotel", "Hotel"),
        ("ground_transport", "Ground Transport"),
        ("unknown", "Unknown"),
    ]

    SCOPE_CHOICES = [
        ("scope_1", "Scope 1"),
        ("scope_2", "Scope 2"),
        ("scope_3", "Scope 3"),
        ("unknown", "Unknown"),
    ]

    STATUS_CHOICES = [
        ("valid", "Valid"),
        ("suspicious", "Suspicious"),
        ("invalid", "Invalid"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    raw_row = models.OneToOneField(
        RawActivityRow,
        on_delete=models.CASCADE,
        related_name="activity_record",
    )

    source_type = models.CharField(max_length=30, choices=SOURCE_TYPES)
    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_TYPES,
        default="unknown",
    )
    scope = models.CharField(
        max_length=30,
        choices=SCOPE_CHOICES,
        default="unknown",
    )

    facility_code = models.CharField(max_length=100, blank=True)
    cost_center = models.CharField(max_length=100, blank=True)

    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    quantity_original = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )
    unit_original = models.CharField(max_length=50, blank=True)

    quantity_normalized = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        null=True,
        blank=True,
    )
    unit_normalized = models.CharField(max_length=50, blank=True)

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=10, blank=True)

    source_reference = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="valid",
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_activity_records",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def can_be_approved(self):
        return self.status in ["valid", "suspicious"] and not self.is_locked

    def __str__(self):
        return f"{self.source_type} - {self.activity_type} - {self.status}"


class ValidationIssue(models.Model):
    SEVERITY_CHOICES = [
        ("error", "Error"),
        ("warning", "Warning"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    activity_record = models.ForeignKey(
        ActivityRecord,
        on_delete=models.CASCADE,
        related_name="issues",
    )

    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    code = models.CharField(max_length=100)
    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.severity}: {self.code}"