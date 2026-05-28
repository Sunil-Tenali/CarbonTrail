# MODEL.md

This file explains the backend data model for CarbonTrail. The main idea is simple: keep the raw source row untouched, create a normalized activity row for review, and record every important action in an audit log.

## Data flow

The backend follows this flow:

1. A CSV file is uploaded with `tenant_id`, `source_type`, and `file`.
2. The upload endpoint chooses the correct importer: SAP, utility, or travel.
3. An `ImportBatch` is created for the file.
4. Each CSV row is saved as a `RawActivityRow`.
5. The importer creates a normalized `ActivityRecord`.
6. Validation issues are created if the row is invalid or suspicious.
7. The analyst can approve or reject the `ActivityRecord`.
8. Approved rows are locked.
9. Imports and analyst actions are written to `AuditLog`.

## Main models

## Tenant

`Tenant` represents one client organization.

Every important table has a `tenant` foreign key. This is the base of the multi-tenant design.

Examples:

- `SourceSystem.tenant`
- `ImportBatch.tenant`
- `RawActivityRow.tenant`
- `ActivityRecord.tenant`
- `ValidationIssue.tenant`
- `AuditLog.tenant`

This keeps records tied to one organization. The current API still needs stronger tenant access checks before real production use, but the data model itself is built around tenant ownership.

## SourceSystem

`SourceSystem` represents where the data came from.

Supported source types:

- `sap`
- `utility`
- `travel`

For this prototype, the source system is created automatically during upload if it does not already exist for that tenant and source type.

Example source systems:

- SAP Fuel and Procurement CSV Upload
- Utility Electricity CSV Upload
- Corporate Travel CSV Upload

This helps answer: “Which source produced this row?”

## ImportBatch

`ImportBatch` represents one uploaded file.

It stores:

- tenant
- source system
- original file name
- uploaded user, if available
- upload time
- processing status
- row counts

The row counts are:

- total rows
- valid rows
- invalid rows
- suspicious rows
- approved rows

This is useful for the upload summary and later review screens.

## RawActivityRow

`RawActivityRow` is the original CSV row saved as JSON.

This is important because the raw row is the source evidence. The normalized data can change or be reviewed, but the original row should stay available for audit and debugging.

It stores:

- tenant
- import batch
- row number
- raw payload
- raw hash
- created time

The raw hash is generated from the payload. It gives a basic way to detect duplicate-looking rows later, although full duplicate handling is not implemented yet.

## ActivityRecord

`ActivityRecord` is the normalized row analysts review.

It stores:

- source type
- activity type
- Scope 1/2/3 classification
- facility code
- cost center
- activity date or period dates
- original quantity and unit
- normalized quantity and unit
- amount and currency
- source reference
- review status
- approval details
- locking details

The link to `RawActivityRow` is one-to-one. That means one raw row produces one normalized activity record.

## ValidationIssue

`ValidationIssue` stores problems found during import.

A row can have multiple issues.

Severity values:

- `error`: the row is invalid
- `warning`: the row is suspicious but can still be reviewed

Examples:

- missing utility meter ID
- invalid billing period
- unsupported unit
- missing flight distance
- missing hotel nights
- unknown SAP unit

The activity status is decided from the issues:

- any error -> `invalid`
- warnings only -> `suspicious`
- no issues -> `valid`

## AuditLog

`AuditLog` stores important system and analyst actions.

It stores:

- tenant
- actor
- action
- entity type
- entity id
- before snapshot
- after snapshot
- message
- timestamp

Current actions include:

- import completed
- import failed
- activity approved
- activity rejected

This is not a replacement for a full compliance audit system, but it proves the basic workflow and gives reviewers a clear trail.

## Scope categorization

The backend assigns scopes during import.

## SAP

SAP rows are classified from the material text.

- fuel-like material -> `scope_1`
- everything else -> `scope_3`

Fuel keywords currently include:

- diesel
- petrol
- gasoline
- fuel
- LPG
- natural gas
- CNG

This is a prototype shortcut. A production system should use material groups, GL accounts, purchasing categories, or a mapping table.

## Utility electricity

Utility electricity rows are always assigned `scope_2`.

This matches the idea that purchased electricity is Scope 2 activity data.

## Corporate travel

Travel rows are always assigned `scope_3`.

The importer supports:

- flights
- hotels
- ground transport

Business travel is treated as an indirect emissions source.

## Unit normalization

The backend stores both original and normalized quantities.

This is intentional.

Example:

- original: `2.5 MWh`
- normalized: `2500 kWh`

This gives analysts both the source value and the cleaned value.

Current normalization:

## SAP

Supported units include:

- liters / litre / ltr / L -> `L`
- gallons -> `L`
- kg -> `kg`
- tonnes / tons -> `kg`

Unknown units are preserved and flagged as warnings.

## Utility

Supported units include:

- kWh -> `kWh`
- MWh -> `kWh`

Unsupported electricity units are validation errors.

## Travel

Travel currently keeps simple activity units:

- flights: km
- hotels: night
- ground transport: km

No CO2e calculation is done yet.

## Source-of-truth tracking

The source-of-truth approach is:

- `SourceSystem` says where the file came from.
- `ImportBatch` says when the file was uploaded.
- `RawActivityRow` stores exactly what was in the source row.
- `ActivityRecord` stores the normalized review version.
- `AuditLog` records important changes after import.

This means an analyst can trace an approved row back to the original uploaded CSV row.

## Approval locking

`ActivityRecord` has:

- `status`
- `approved_by`
- `approved_at`
- `is_locked`
- `locked_at`

Only `valid` or `suspicious` unlocked rows can be approved.

When a row is approved:

- status becomes `approved`
- `is_locked` becomes true
- approval timestamp is saved
- audit log is created

Locked rows cannot be edited through the update API.

This matches the assignment requirement that analysts approve rows before they are locked for audit.

## Filtering support

The activity record API supports filters useful for a review dashboard:

- tenant
- source type
- scope
- status
- activity type
- import batch
- validation state

Validation state can filter rows with issues, errors, or warnings.

## Production improvements

If this became a real product, I would improve the model in these ways:

1. Add real authentication and tenant permissions.
2. Add mapping tables for plant codes, meters, material groups, and travel categories.
3. Add duplicate detection across import batches using `raw_hash`.
4. Add a full emissions-factor calculation layer for CO2e.
5. Add version history for analyst edits, not only approval/rejection snapshots.
6. Add background jobs for large files.
7. Add stricter database constraints for approved locked records.
8. Add file storage for the original uploaded CSV, not only row payloads.
9. Add support for partial approval by batch and bulk review actions.
10. Add PostgreSQL indexes after real query patterns are known.
