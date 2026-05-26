"""
Activities app - Core emissions data model for CarbonTrail.

This is the central business logic module. ActivityRecord represents
processed emissions data ready for reporting and compliance.

DATAFLOW:
1. RawActivityRow imported from external system
2. Validation rules applied, issues collected
3. ActivityRecord created with initial status
4. User reviews and approves records
5. Approved activities used in reports

GHG PROTOCOL SCOPES (international standard):
- Scope 1: Direct emissions (company vehicles, on-site fuel)
- Scope 2: Indirect energy (purchased electricity)
- Scope 3: Other indirect (business travel, supply chain)
"""

from django.conf import settings
from django.db import models
from organizations.models import Tenant
from ingestion.models import RawActivityRow


class ActivityRecord(models.Model):
    """
    A single emissions activity record for reporting and compliance.

    This is the primary data model - each record represents one emissions
    event or consumption period from an organization.

    DESIGN NOTES:
    - source_type: WHERE data came from (SAP, utility, travel system)
    - activity_type: WHAT was emitted (fuel, electricity, flight, etc.)
    - Stores both original and normalized quantities for audit trail
    - Status workflow: valid → suspicious → invalid or → approved/rejected
    - is_locked: Prevents modification for compliance period immutability
    """

    # Classification choices for emissions tracking
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

    # GHG Protocol standard scopes
    SCOPE_CHOICES = [
        ("scope_1", "Scope 1"),  # Direct emissions
        ("scope_2", "Scope 2"),  # Indirect energy
        ("scope_3", "Scope 3"),  # Other indirect
        ("unknown", "Unknown"),
    ]

    # Approval workflow states
    STATUS_CHOICES = [
        ("valid", "Valid"),          # Passed validation
        ("suspicious", "Suspicious"),  # Warnings but usable
        ("invalid", "Invalid"),    # Has errors
        ("approved", "Approved"),  # User approved
        ("rejected", "Rejected"),  # User rejected
    ]

    # Multi-tenancy: Every activity belongs to one organization
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    # Link to immutable source data
    raw_row = models.OneToOneField(
        RawActivityRow,
        on_delete=models.CASCADE,
        related_name="activity_record",
    )

    # Activity classification
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPES)
    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_TYPES,
        default="unknown",
    )
    # GHG Protocol scope
    scope = models.CharField(
        max_length=30,
        choices=SCOPE_CHOICES,
        default="unknown",
    )

    # Location & cost tracking for allocation
    facility_code = models.CharField(max_length=100, blank=True)
    cost_center = models.CharField(max_length=100, blank=True)

    # Timing: Either activity_date OR period_start/period_end
    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    # Quantity: Original (as received) and normalized (for calculations)
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

    # Financial information
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=10, blank=True)

    # External reference for traceability
    source_reference = models.CharField(max_length=255, blank=True)

    # Approval workflow status
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="valid",
    )

    # Audit trail: Who approved and when
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_activity_records",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Compliance: Lock prevents modification after approval
    is_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)

    # Lifecycle tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def can_be_approved(self):
        """
        Check if record can be approved.
        Only valid/suspicious records and unlocked records can be approved.
        """
        return self.status in ["valid", "suspicious"] and not self.is_locked

    def __str__(self):
        return f"{self.source_type} - {self.activity_type} - {self.status}"


class ValidationIssue(models.Model):
    """
    A validation problem found with an ActivityRecord.

    Validation rules are applied during import:
    - Errors: Critical issues preventing use (invalid format, missing data)
    - Warnings: Issues worth noting but data still usable (outliers)

    Examples:
    - Error: "MISSING_FACILITY_ID" - Facility code required
    - Warning: "OUTLIER_QUANTITY" - Usage 10x above normal
    - Error: "INVALID_SCOPE" - Scope type not recognized
    - Warning: "FUTURE_DATE" - Activity date in future
    """

    SEVERITY_CHOICES = [
        ("error", "Error"),      # Critical, blocks use
        ("warning", "Warning"),  # Warning, allows use
    ]

    # Which organization
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    # The activity record that has this issue
    activity_record = models.ForeignKey(
        ActivityRecord,
        on_delete=models.CASCADE,
        related_name="issues",
    )

    # Severity level
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    # Machine-readable issue type code
    code = models.CharField(max_length=100)
    # Human-readable explanation
    message = models.TextField()

    # When detected
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.severity}: {self.code}"