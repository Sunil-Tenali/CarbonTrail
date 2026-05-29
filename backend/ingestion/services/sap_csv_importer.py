from datetime import date
from decimal import Decimal

from django.db import transaction

from activities.models import ActivityRecord, ValidationIssue
from audit.models import AuditLog
from ingestion.models import ImportBatch, RawActivityRow

from .common import (
    get_first_value,
    open_uploaded_csv,
    parse_date,
    parse_decimal,
    status_from_issues,
)


UNIT_NORMALIZATION_MAP = {
    "l": ("L", Decimal("1")),
    "ltr": ("L", Decimal("1")),
    "liter": ("L", Decimal("1")),
    "litre": ("L", Decimal("1")),
    "liters": ("L", Decimal("1")),
    "litres": ("L", Decimal("1")),

    "gal": ("L", Decimal("3.78541")),
    "gallon": ("L", Decimal("3.78541")),
    "gallons": ("L", Decimal("3.78541")),

    "kg": ("kg", Decimal("1")),
    "kilogram": ("kg", Decimal("1")),
    "kilograms": ("kg", Decimal("1")),

    "t": ("kg", Decimal("1000")),
    "ton": ("kg", Decimal("1000")),
    "tonne": ("kg", Decimal("1000")),
    "tons": ("kg", Decimal("1000")),
    "tonnes": ("kg", Decimal("1000")),
}


FUEL_KEYWORDS = [
    "diesel",
    "petrol",
    "gasoline",
    "fuel",
    "lpg",
    "natural gas",
    "cng",
]


def normalize_unit(quantity, unit):
    """
    Normalize SAP units to standard forms (liters, kilograms).
    Returns normalized quantity and unit, or original if unknown.
    """
    if quantity is None:
        return None, ""

    if unit is None:
        return quantity, ""

    unit_key = str(unit).strip().lower()

    if unit_key not in UNIT_NORMALIZATION_MAP:
        return quantity, str(unit).strip()

    normalized_unit, factor = UNIT_NORMALIZATION_MAP[unit_key]
    normalized_quantity = quantity * factor

    return normalized_quantity, normalized_unit


def classify_activity(material_name):
    """
    Classify SAP material as fuel (Scope 1) or procurement (Scope 3).
    - Fuel (Scope 1): Direct emissions from company operations
    - Procurement (Scope 3): Purchased goods and services
    """
    material_text = str(material_name or "").lower()

    for keyword in FUEL_KEYWORDS:
        if keyword in material_text:
            return "fuel", "scope_1"

    return "procurement", "scope_3"


class SAPCSVImporter:
    """
    Imports SAP fuel and procurement CSV exports.

    Classifies materials as:
    - Fuel (Scope 1): Direct company operations
    - Procurement (Scope 3): Purchased goods and services

    Normalizes units (L, kg, tonnes) and preserves raw rows for audit trail.
    """

    def __init__(self, tenant, source_system, uploaded_by=None):
        self.tenant = tenant
        self.source_system = source_system
        self.uploaded_by = uploaded_by

    def import_file(self, uploaded_file):
        batch = ImportBatch.objects.create(
            tenant=self.tenant,
            source_system=self.source_system,
            original_filename=uploaded_file.name,
            uploaded_by=self.uploaded_by,
            status="processing",
        )

        try:
            reader = open_uploaded_csv(uploaded_file)

            if reader.fieldnames is None:
                batch.status = "failed"
                batch.save(update_fields=["status"])
                return batch

            total_rows = 0

            for row_number, row in enumerate(reader, start=1):
                total_rows += 1
                self.process_row(batch, row_number, row)

            self.update_batch_counts(batch, total_rows)

            AuditLog.objects.create(
                tenant=self.tenant,
                actor=self.uploaded_by,
                action="imported",
                entity_type="ImportBatch",
                entity_id=batch.id,
                before=None,
                after={
                    "source_type": "sap",
                    "status": batch.status,
                    "total_rows": batch.total_rows,
                    "valid_rows": batch.valid_rows,
                    "invalid_rows": batch.invalid_rows,
                    "suspicious_rows": batch.suspicious_rows,
                    "approved_rows": batch.approved_rows,
                },
                message="SAP fuel/procurement CSV imported and normalized.",
            )

            return batch

        except Exception as error:
            batch.status = "failed"
            batch.save(update_fields=["status"])

            AuditLog.objects.create(
                tenant=self.tenant,
                actor=self.uploaded_by,
                action="import_failed",
                entity_type="ImportBatch",
                entity_id=batch.id,
                before=None,
                after={
                    "source_type": "sap",
                    "error": str(error),
                },
                message="SAP CSV import failed.",
            )

            return batch

    @transaction.atomic
    def process_row(self, batch, row_number, row):
        raw_row = RawActivityRow.objects.create(
            tenant=self.tenant,
            import_batch=batch,
            row_number=row_number,
            raw_payload=dict(row),
        )

        document_number = get_first_value(
            row,
            [
                "Document Number",
                "Material Document",
                "Material Doc",
                "Document No",
                "Belegnummer",
            ],
        )

        posting_date_text = get_first_value(
            row,
            [
                "Posting Date",
                "Document Date",
                "Buchungsdatum",
                "PostingDate",
            ],
        )

        plant = get_first_value(
            row,
            [
                "Plant",
                "Werk",
                "Facility",
                "Facility Code",
                "Plant Code",
            ],
        )

        cost_center = get_first_value(
            row,
            [
                "Cost Center",
                "Kostenstelle",
                "CostCenter",
            ],
        )

        material = get_first_value(
            row,
            [
                "Material",
                "Material Description",
                "Material Name",
                "Materialkurztext",
                "Item Description",
                "Description",
            ],
        )

        quantity_text = get_first_value(
            row,
            [
                "Quantity",
                "Qty",
                "Menge",
                "Order Quantity",
                "Movement Quantity",
            ],
        )

        unit = get_first_value(
            row,
            [
                "UoM",
                "Unit",
                "Unit of Measure",
                "Base Unit of Measure",
                "ME",
            ],
        )

        amount_text = get_first_value(
            row,
            [
                "Amount",
                "Value",
                "Net Value",
                "Betrag",
                "Local Currency Amount",
            ],
        )

        currency = get_first_value(
            row,
            [
                "Currency",
                "Währung",
                "Currency Code",
            ],
        )

        activity_date = parse_date(posting_date_text)
        quantity_original = parse_decimal(quantity_text)
        amount = parse_decimal(amount_text)

        quantity_normalized, unit_normalized = normalize_unit(
            quantity_original,
            unit,
        )

        activity_type, scope = classify_activity(material)

        issues = []

        if not plant:
            issues.append(
                {
                    "severity": "error",
                    "code": "MISSING_PLANT",
                    "message": "SAP row is missing plant/facility code.",
                }
            )

        if not material:
            issues.append(
                {
                    "severity": "warning",
                    "code": "MISSING_MATERIAL_DESCRIPTION",
                    "message": "SAP row is missing material description.",
                }
            )

        if activity_date is None:
            issues.append(
                {
                    "severity": "error",
                    "code": "INVALID_POSTING_DATE",
                    "message": "Posting date is missing or not in a supported format.",
                }
            )

        if quantity_original is None:
            issues.append(
                {
                    "severity": "error",
                    "code": "INVALID_QUANTITY",
                    "message": "Quantity is missing or is not a valid number.",
                }
            )

        if quantity_original is not None and quantity_original <= 0:
            issues.append(
                {
                    "severity": "error",
                    "code": "NON_POSITIVE_QUANTITY",
                    "message": "Quantity must be greater than zero.",
                }
            )

        if unit:
            unit_key = unit.strip().lower()

            if unit_key not in UNIT_NORMALIZATION_MAP:
                issues.append(
                    {
                        "severity": "warning",
                        "code": "UNKNOWN_UNIT",
                        "message": (
                            f"Unit '{unit}' was not recognized, "
                            "so the original unit was preserved."
                        ),
                    }
                )
        else:
            issues.append(
                {
                    "severity": "error",
                    "code": "MISSING_UNIT",
                    "message": "SAP row is missing a unit of measure.",
                }
            )

        if quantity_original is not None and quantity_original > Decimal("100000"):
            issues.append(
                {
                    "severity": "warning",
                    "code": "OUTLIER_QUANTITY",
                    "message": "Quantity is unusually high and should be reviewed.",
                }
            )

        if activity_date is not None and activity_date > date.today():
            issues.append(
                {
                    "severity": "warning",
                    "code": "FUTURE_DATE",
                    "message": "Posting date is in the future.",
                }
            )

        status = status_from_issues(issues)

        activity_record = ActivityRecord.objects.create(
            tenant=self.tenant,
            raw_row=raw_row,
            source_type="sap",
            activity_type=activity_type,
            scope=scope,
            facility_code=plant,
            cost_center=cost_center,
            activity_date=activity_date,
            quantity_original=quantity_original,
            unit_original=unit,
            quantity_normalized=quantity_normalized,
            unit_normalized=unit_normalized,
            amount=amount,
            currency=currency,
            source_reference=document_number,
            status=status,
        )

        for issue in issues:
            ValidationIssue.objects.create(
                tenant=self.tenant,
                activity_record=activity_record,
                severity=issue["severity"],
                code=issue["code"],
                message=issue["message"],
            )

    def update_batch_counts(self, batch, total_rows):
        activity_records = ActivityRecord.objects.filter(
            raw_row__import_batch=batch,
        )

        batch.total_rows = total_rows
        batch.valid_rows = activity_records.filter(status="valid").count()
        batch.invalid_rows = activity_records.filter(status="invalid").count()
        batch.suspicious_rows = activity_records.filter(status="suspicious").count()
        batch.approved_rows = activity_records.filter(status="approved").count()
        batch.status = "completed"

        batch.save(
            update_fields=[
                "total_rows",
                "valid_rows",
                "invalid_rows",
                "suspicious_rows",
                "approved_rows",
                "status",
            ]
        )