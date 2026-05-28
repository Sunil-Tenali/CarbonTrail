from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from rest_framework.test import APIClient

from activities.models import ActivityRecord, ValidationIssue
from audit.models import AuditLog
from ingestion.models import ImportBatch, RawActivityRow, SourceSystem
from ingestion.services.sap_csv_importer import SAPCSVImporter
from ingestion.services.travel_csv_importer import TravelCSVImporter
from ingestion.services.utility_csv_importer import UtilityElectricityCSVImporter
from organizations.models import Tenant


class ImporterTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Acme Manufacturing")
        self.user = User.objects.create_user(
            username="analyst",
            password="pass",
        )

    def make_csv_file(self, filename, content):
        return SimpleUploadedFile(
            filename,
            content.encode("utf-8"),
            content_type="text/csv",
        )

    def make_source_system(self, source_type):
        return SourceSystem.objects.create(
            tenant=self.tenant,
            name=f"{source_type.title()} CSV",
            source_type=source_type,
        )

    def make_activity_record(self, status="valid"):
        source = self.make_source_system("utility")

        batch = ImportBatch.objects.create(
            tenant=self.tenant,
            source_system=source,
            original_filename="test.csv",
            uploaded_by=self.user,
            status="completed",
            total_rows=1,
            valid_rows=1,
        )

        raw_row = RawActivityRow.objects.create(
            tenant=self.tenant,
            import_batch=batch,
            row_number=1,
            raw_payload={
                "meter_id": "MTR-TEST-1",
                "usage_quantity": "100",
                "usage_unit": "kWh",
            },
        )

        return ActivityRecord.objects.create(
            tenant=self.tenant,
            raw_row=raw_row,
            source_type="utility",
            activity_type="electricity",
            scope="scope_2",
            facility_code="BLR01",
            quantity_original=Decimal("100"),
            unit_original="kWh",
            quantity_normalized=Decimal("100"),
            unit_normalized="kWh",
            source_reference="MTR-TEST-1",
            status=status,
        )

    def test_sap_import_creates_raw_and_normalized_rows(self):
        source = self.make_source_system("sap")

        csv_text = (
            "Document Number,Posting Date,Plant,Material,Quantity,UoM,Amount,Currency\n"
            "SAP-1001,2024-01-01,BLR01,Diesel for generator,100,L,9000,INR\n"
        )

        importer = SAPCSVImporter(
            self.tenant,
            source,
            self.user,
        )
        importer.import_file(self.make_csv_file("sap.csv", csv_text))

        self.assertEqual(RawActivityRow.objects.count(), 1)
        self.assertEqual(ActivityRecord.objects.count(), 1)

        record = ActivityRecord.objects.get()

        self.assertEqual(record.source_type, "sap")
        self.assertEqual(record.activity_type, "fuel")
        self.assertEqual(record.scope, "scope_1")
        self.assertEqual(record.quantity_normalized, Decimal("100"))
        self.assertEqual(record.unit_normalized, "L")

    def test_utility_mwh_is_normalized_to_kwh(self):
        source = self.make_source_system("utility")

        csv_text = (
            "meter_id,facility_code,billing_period_start,billing_period_end,"
            "usage_quantity,usage_unit,demand_kw,tariff_name,amount,currency\n"
            "MTR-1,BLR01,2024-01-01,2024-01-31,2.5,MWh,10,HT,1000,INR\n"
        )

        importer = UtilityElectricityCSVImporter(
            self.tenant,
            source,
            self.user,
        )
        importer.import_file(self.make_csv_file("utility.csv", csv_text))

        record = ActivityRecord.objects.get()

        self.assertEqual(record.source_type, "utility")
        self.assertEqual(record.activity_type, "electricity")
        self.assertEqual(record.scope, "scope_2")
        self.assertEqual(record.unit_normalized, "kWh")
        self.assertEqual(record.quantity_normalized, Decimal("2500.0"))

    def test_utility_invalid_billing_period_is_flagged(self):
        source = self.make_source_system("utility")

        csv_text = (
            "meter_id,facility_code,billing_period_start,billing_period_end,"
            "usage_quantity,usage_unit,demand_kw,tariff_name,amount,currency\n"
            "MTR-1,BLR01,2024-02-28,2024-02-01,100,kWh,10,HT,1000,INR\n"
        )

        importer = UtilityElectricityCSVImporter(
            self.tenant,
            source,
            self.user,
        )
        importer.import_file(self.make_csv_file("utility.csv", csv_text))

        record = ActivityRecord.objects.get()

        self.assertEqual(record.status, "invalid")
        self.assertTrue(
            ValidationIssue.objects.filter(
                activity_record=record,
                code="INVALID_BILLING_PERIOD_RANGE",
            ).exists()
        )

    def test_travel_missing_flight_distance_is_flagged(self):
        source = self.make_source_system("travel")

        csv_text = (
            "trip_id,employee_id,category,booking_date,start_date,end_date,"
            "origin_airport,destination_airport,distance_km,hotel_nights,"
            "ground_transport_mode,amount,currency\n"
            "TRIP-1,E001,flight,2024-01-01,2024-01-02,2024-01-02,"
            "BLR,DEL,,,,1000,INR\n"
        )

        importer = TravelCSVImporter(
            self.tenant,
            source,
            self.user,
        )
        importer.import_file(self.make_csv_file("travel.csv", csv_text))

        record = ActivityRecord.objects.get()

        self.assertEqual(record.source_type, "travel")
        self.assertEqual(record.scope, "scope_3")
        self.assertEqual(record.status, "invalid")
        self.assertTrue(
            ValidationIssue.objects.filter(
                activity_record=record,
                code="MISSING_FLIGHT_DISTANCE",
            ).exists()
        )

    def test_travel_hotel_missing_nights_is_flagged(self):
        source = self.make_source_system("travel")

        csv_text = (
            "trip_id,employee_id,category,booking_date,start_date,end_date,"
            "origin_airport,destination_airport,distance_km,hotel_nights,"
            "ground_transport_mode,amount,currency\n"
            "TRIP-2,E002,hotel,2024-01-01,2024-01-02,2024-01-05,"
            ",,,,,5000,INR\n"
        )

        importer = TravelCSVImporter(
            self.tenant,
            source,
            self.user,
        )
        importer.import_file(self.make_csv_file("travel.csv", csv_text))

        record = ActivityRecord.objects.get()

        self.assertEqual(record.source_type, "travel")
        self.assertEqual(record.activity_type, "hotel")
        self.assertEqual(record.scope, "scope_3")
        self.assertEqual(record.status, "invalid")
        self.assertTrue(
            ValidationIssue.objects.filter(
                activity_record=record,
                code="MISSING_HOTEL_NIGHTS",
            ).exists()
        )

    def test_raw_row_is_preserved_for_utility_import(self):
        source = self.make_source_system("utility")

        csv_text = (
            "meter_id,facility_code,billing_period_start,billing_period_end,"
            "usage_quantity,usage_unit,demand_kw,tariff_name,amount,currency\n"
            "MTR-RAW,BLR01,2024-01-01,2024-01-31,50,kWh,10,HT,1000,INR\n"
        )

        importer = UtilityElectricityCSVImporter(
            self.tenant,
            source,
            self.user,
        )
        importer.import_file(self.make_csv_file("utility.csv", csv_text))

        self.assertEqual(RawActivityRow.objects.count(), 1)

        raw_row = RawActivityRow.objects.get()
        self.assertEqual(raw_row.raw_payload["meter_id"], "MTR-RAW")

    def test_import_creates_audit_log(self):
        source = self.make_source_system("utility")

        csv_text = (
            "meter_id,facility_code,billing_period_start,billing_period_end,"
            "usage_quantity,usage_unit,demand_kw,tariff_name,amount,currency\n"
            "MTR-1,BLR01,2024-01-01,2024-01-31,100,kWh,10,HT,1000,INR\n"
        )

        importer = UtilityElectricityCSVImporter(
            self.tenant,
            source,
            self.user,
        )
        importer.import_file(self.make_csv_file("utility.csv", csv_text))

        self.assertTrue(
            AuditLog.objects.filter(
                action="imported",
                entity_type="ImportBatch",
            ).exists()
        )

    def test_approval_locks_row_and_creates_audit_log(self):
        record = self.make_activity_record(status="valid")

        client = APIClient()
        client.force_authenticate(user=self.user)

        response = client.post(f"/api/activity-records/{record.id}/approve/")

        self.assertEqual(response.status_code, 200)

        record.refresh_from_db()

        self.assertEqual(record.status, "approved")
        self.assertTrue(record.is_locked)
        self.assertIsNotNone(record.approved_at)
        self.assertIsNotNone(record.locked_at)
        self.assertEqual(record.approved_by, self.user)

        self.assertTrue(
            AuditLog.objects.filter(
                action="approved",
                entity_type="ActivityRecord",
                entity_id=record.id,
            ).exists()
        )

    def test_approved_locked_row_cannot_be_edited(self):
        record = self.make_activity_record(status="valid")

        client = APIClient()
        client.force_authenticate(user=self.user)

        approve_response = client.post(
            f"/api/activity-records/{record.id}/approve/"
        )
        self.assertEqual(approve_response.status_code, 200)

        edit_response = client.patch(
            f"/api/activity-records/{record.id}/",
            {"facility_code": "CHANGED"},
            format="json",
        )

        self.assertEqual(edit_response.status_code, 400)

        record.refresh_from_db()
        self.assertNotEqual(record.facility_code, "CHANGED")

    def test_rejection_marks_row_rejected_and_creates_audit_log(self):
        record = self.make_activity_record(status="invalid")

        client = APIClient()
        client.force_authenticate(user=self.user)

        response = client.post(
            f"/api/activity-records/{record.id}/reject/",
            {"reason": "Missing required source evidence."},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        record.refresh_from_db()

        self.assertEqual(record.status, "rejected")
        self.assertFalse(record.is_locked)

        self.assertTrue(
            AuditLog.objects.filter(
                action="rejected",
                entity_type="ActivityRecord",
                entity_id=record.id,
                message="Missing required source evidence.",
            ).exists()
        )