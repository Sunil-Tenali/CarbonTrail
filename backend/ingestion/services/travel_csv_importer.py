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


KNOWN_GROUND_MODES = {
    "taxi",
    "rideshare",
    "rental_car",
    "train",
    "bus",
    "car",
}


class TravelCSVImporter:
    """
    Imports corporate travel CSV exports (flights, hotels, ground transport).

    Real-world data shape:
    Concur, Navan, and similar expense platforms export trip records with
    category (flight/hotel/ground), dates, distance, origin/destination
    (flights), nights (hotels), transport mode (ground), and amount.

    Prototype scope:
    - Each row is one trip or trip segment
    - Supports flights (distance km), hotels (nights), ground transport (mode)
    - All classified as Scope 3 (business travel)
    - Normalizes ground transport modes (taxi, rental, train, etc.)
    - Preserves raw rows as RawActivityRow
    - Validates required fields per category, flags unknown modes
    - Warnings for missing trip/employee IDs

    GHG Protocol:
    All business travel is Scope 3 (other indirect). Distance-based
    (flights, ground) and night-based (hotels) approaches are simplified
    prototypes; real carbon calculations would use actual emission factors
    per route/airline/mode and convert to CO2e.
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
                    "source_type": "travel",
                    "total_rows": batch.total_rows,
                    "valid_rows": batch.valid_rows,
                    "invalid_rows": batch.invalid_rows,
                    "suspicious_rows": batch.suspicious_rows,
                },
                message="Corporate travel CSV imported and normalized.",
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
                message="Corporate travel CSV import failed.",
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

        trip_id = get_first_value(row, ["trip_id", "Trip ID"])
        employee_id = get_first_value(row, ["employee_id", "Employee ID"])
        category = get_first_value(row, ["category", "Category"]).lower()

        booking_date = parse_date(get_first_value(row, ["booking_date", "Booking Date"]))
        start_date = parse_date(get_first_value(row, ["start_date", "Start Date"]))
        end_date = parse_date(get_first_value(row, ["end_date", "End Date"]))

        origin_airport = get_first_value(row, ["origin_airport", "Origin Airport"])
        destination_airport = get_first_value(
            row,
            ["destination_airport", "Destination Airport"],
        )

        distance_km = parse_decimal(get_first_value(row, ["distance_km", "Distance KM"]))
        hotel_nights = parse_decimal(get_first_value(row, ["hotel_nights", "Hotel Nights"]))
        ground_mode = get_first_value(
            row,
            ["ground_transport_mode", "Ground Transport Mode"],
        ).lower()

        amount = parse_decimal(get_first_value(row, ["amount", "Amount"]))
        currency = get_first_value(row, ["currency", "Currency"])

        issues = []

        if not trip_id:
            issues.append({
                "severity": "warning",
                "code": "MISSING_TRIP_ID",
                "message": "Travel row is missing trip_id.",
            })

        if category not in ["flight", "hotel", "ground_transport"]:
            issues.append({
                "severity": "error",
                "code": "UNKNOWN_TRAVEL_CATEGORY",
                "message": f"Travel category '{category}' is not supported.",
            })

        quantity_original = None
        unit_original = ""
        quantity_normalized = None
        unit_normalized = ""

        activity_type = category if category in ["flight", "hotel"] else "ground_transport"

        if category == "flight":
            quantity_original = distance_km
            unit_original = "km"
            quantity_normalized = distance_km
            unit_normalized = "km"

            if not origin_airport or not destination_airport:
                issues.append({
                    "severity": "error",
                    "code": "MISSING_AIRPORT_CODES",
                    "message": "Flight row must include origin and destination airport codes.",
                })

            if distance_km is None:
                issues.append({
                    "severity": "error",
                    "code": "MISSING_FLIGHT_DISTANCE",
                    "message": "Flight row is missing distance_km.",
                })

        elif category == "hotel":
            quantity_original = hotel_nights
            unit_original = "night"
            quantity_normalized = hotel_nights
            unit_normalized = "night"

            if hotel_nights is None:
                issues.append({
                    "severity": "error",
                    "code": "MISSING_HOTEL_NIGHTS",
                    "message": "Hotel row is missing hotel_nights.",
                })

        elif category == "ground_transport":
            quantity_original = distance_km
            unit_original = "km"
            quantity_normalized = distance_km
            unit_normalized = "km"

            if ground_mode not in KNOWN_GROUND_MODES:
                issues.append({
                    "severity": "warning",
                    "code": "UNKNOWN_GROUND_TRANSPORT_MODE",
                    "message": f"Ground transport mode '{ground_mode}' is not recognized.",
                })

        status = status_from_issues(issues)

        activity_record = ActivityRecord.objects.create(
            tenant=self.tenant,
            raw_row=raw_row,
            source_type="travel",
            activity_type=activity_type,
            scope="scope_3",
            activity_date=booking_date,
            period_start=start_date,
            period_end=end_date,
            quantity_original=quantity_original,
            unit_original=unit_original,
            quantity_normalized=quantity_normalized,
            unit_normalized=unit_normalized,
            amount=amount,
            currency=currency,
            source_reference=trip_id or employee_id,
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