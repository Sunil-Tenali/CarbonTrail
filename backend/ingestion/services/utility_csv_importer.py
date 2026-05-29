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


UTILITY_UNIT_MAP = {
    "kwh": ("kWh", Decimal("1")),
    "kw h": ("kWh", Decimal("1")),
    "mwh": ("kWh", Decimal("1000")),
}


class UtilityElectricityCSVImporter:
    """
    Imports utility electricity billing CSV exports.

    All records classified as Scope 2 (purchased electricity).
    Normalizes units (kWh, MWh) and preserves raw rows for audit trail.
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
                    "source_type": "utility",
                    "total_rows": batch.total_rows,
                    "valid_rows": batch.valid_rows,
                    "invalid_rows": batch.invalid_rows,
                    "suspicious_rows": batch.suspicious_rows,
                },
                message="Utility electricity CSV imported and normalized.",
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
                after={"error": str(error)},
                message="Utility electricity CSV import failed.",
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

        meter_id = get_first_value(row, ["meter_id", "Meter ID", "Meter"])
        facility_code = get_first_value(
            row,
            ["facility_code", "Facility Code", "Plant"],
        )

        period_start = parse_date(
            get_first_value(row, ["billing_period_start", "Start Date"])
        )
        period_end = parse_date(
            get_first_value(row, ["billing_period_end", "End Date"])
        )

        usage_quantity = parse_decimal(
            get_first_value(row, ["usage_quantity", "Usage", "Consumption"])
        )
        usage_unit = get_first_value(row, ["usage_unit", "Unit", "UOM"])

        demand_kw = parse_decimal(get_first_value(row, ["demand_kw", "Demand kW"]))
        amount = parse_decimal(get_first_value(row, ["amount", "Amount"]))
        currency = get_first_value(row, ["currency", "Currency"])
        tariff_name = get_first_value(row, ["tariff_name", "Tariff"])

        issues = []

        normalized_quantity = usage_quantity
        normalized_unit = usage_unit

        unit_key = usage_unit.strip().lower()

        if not meter_id:
            issues.append({
                "severity": "error",
                "code": "MISSING_METER_ID",
                "message": "Utility row is missing meter_id.",
            })

        if period_start is None or period_end is None:
            issues.append({
                "severity": "error",
                "code": "INVALID_BILLING_PERIOD_DATE",
                "message": "Billing period start or end date is invalid.",
            })

        if period_start and period_end and period_end < period_start:
            issues.append({
                "severity": "error",
                "code": "INVALID_BILLING_PERIOD_RANGE",
                "message": "Billing period end date is before start date.",
            })

        if usage_quantity is None:
            issues.append({
                "severity": "error",
                "code": "INVALID_USAGE_QUANTITY",
                "message": "Usage quantity is missing or invalid.",
            })

        if usage_quantity is not None and usage_quantity <= 0:
            issues.append({
                "severity": "error",
                "code": "NON_POSITIVE_USAGE",
                "message": "Electricity usage must be greater than zero.",
            })

        if unit_key in UTILITY_UNIT_MAP and usage_quantity is not None:
            normalized_unit, factor = UTILITY_UNIT_MAP[unit_key]
            normalized_quantity = usage_quantity * factor
        else:
            issues.append({
                "severity": "error",
                "code": "UNSUPPORTED_ELECTRICITY_UNIT",
                "message": f"Electricity unit '{usage_unit}' is not supported.",
            })

        if normalized_quantity is not None and normalized_quantity > Decimal("1000000"):
            issues.append({
                "severity": "warning",
                "code": "HIGH_ELECTRICITY_USAGE",
                "message": "Electricity usage is unusually high and should be reviewed.",
            })

        status = status_from_issues(issues)

        activity_record = ActivityRecord.objects.create(
            tenant=self.tenant,
            raw_row=raw_row,
            source_type="utility",
            activity_type="electricity",
            scope="scope_2",
            facility_code=facility_code,
            period_start=period_start,
            period_end=period_end,
            quantity_original=usage_quantity,
            unit_original=usage_unit,
            quantity_normalized=normalized_quantity,
            unit_normalized=normalized_unit,
            amount=amount,
            currency=currency,
            source_reference=meter_id,
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
        activity_records = ActivityRecord.objects.filter(raw_row__import_batch=batch)

        batch.total_rows = total_rows
        batch.valid_rows = activity_records.filter(status="valid").count()
        batch.invalid_rows = activity_records.filter(status="invalid").count()
        batch.suspicious_rows = activity_records.filter(status="suspicious").count()
        batch.approved_rows = activity_records.filter(status="approved").count()
        batch.status = "completed"

        batch.save()