# MODEL.md

This document explains the data model I used for CarbonTrail and why I chose it.

The basic idea is:

1. Keep the original source row.
2. Create a normalized activity row from it.
3. Attach validation issues if something is missing or suspicious.
4. Let an analyst approve or reject the normalized row.
5. Lock approved rows and write audit logs.

I wanted the model to make the review process easy to explain. If someone asks where a number came from, the app should be able to point back to the uploaded file row and the import batch.

## Main data flow

```text
Tenant
  -> SourceSystem
  -> ImportBatch
  -> RawActivityRow
  -> ActivityRecord
  -> ValidationIssue
  -> AuditLog
```

When a CSV is uploaded:

1. The frontend sends `tenant_id`, `source_type`, and the file.
2. The backend chooses the correct importer.
3. The backend creates an `ImportBatch`.
4. Every CSV row is saved as a `RawActivityRow`.
5. A normalized `ActivityRecord` is created from each raw row.
6. Validation issues are added when needed.
7. Analysts can approve or reject records.
8. Audit logs are written for imports and review actions.

## Tenant

`Tenant` represents a client company.

Examples:

- Acme Manufacturing
- Test company
- A real enterprise client in a production setup

Every important model connects back to `Tenant`. That is the base of multi-tenancy in this prototype.

Models with tenant ownership:

- `SourceSystem`
- `ImportBatch`
- `RawActivityRow`
- `ActivityRecord`
- `ValidationIssue`
- `AuditLog`

This means rows from one company are not mixed with rows from another company at the data model level. The current prototype still uses open API permissions, so production would need request-level tenant access control too.

## SourceSystem

`SourceSystem` stores where a file came from.

Supported source types:

```text
sap
utility
travel
```

For this assignment, the source systems are created automatically during upload. For example, if a company uploads a utility file, the backend creates or reuses a source system for utility electricity CSV upload.

This helps answer:

```text
Which system produced this row?
```

## ImportBatch

`ImportBatch` represents one uploaded CSV file.

It stores:

- company/tenant
- source system
- original filename
- uploaded user if available
- upload time
- import status
- total row count
- valid row count
- invalid row count
- suspicious row count
- approved row count

This is used by the Import Batches frontend page. I kept batch counts directly on the model because they are useful for the analyst and simple to display.

## RawActivityRow

`RawActivityRow` stores the original CSV row as JSON.

This is one of the more important parts of the model. The normalized row may be easier to review, but the raw row is the evidence. Analysts can open a row detail page and compare the normalized fields against the original payload.

It stores:

- tenant
- import batch
- row number
- raw payload
- raw hash
- created time

The raw hash is there as a small start toward duplicate detection. I did not build full duplicate handling, but the field gives a place to build from.

## ActivityRecord

`ActivityRecord` is the normalized row the analyst reviews.

It stores:

- tenant
- raw row link
- source type
- activity type
- Scope 1 / Scope 2 / Scope 3 category
- facility code
- cost center
- activity date or period start/end
- original quantity and unit
- normalized quantity and unit
- amount and currency when available
- source reference such as meter ID, SAP document number, or trip ID
- status
- approval fields
- lock fields

The one-to-one link with `RawActivityRow` keeps the normalized row tied to exactly one source row.

## ValidationIssue

`ValidationIssue` stores row-level problems found during import.

Severity values:

```text
error    -> row is invalid
warning  -> row is suspicious and needs attention
```

Examples:

- missing meter ID
- invalid billing period
- unsupported electricity unit
- missing flight distance
- missing hotel nights
- unknown SAP unit
- suspiciously high quantity

The importer uses issues to set the initial activity status:

```text
error exists       -> invalid
only warnings      -> suspicious
no issues          -> valid
```

I kept validation issues separate from `ActivityRecord` instead of putting one text field on the record. A row can have more than one issue, and the frontend can show each one clearly.

## AuditLog

`AuditLog` records important actions.

Current actions:

- `imported`
- `import_failed`
- `approved`
- `rejected`

The log stores:

- tenant
- actor, if logged in
- action
- entity type
- entity ID
- before snapshot
- after snapshot
- message
- created time

This is used in both the row detail page and the audit logs page.

Approved rows are locked. Rejected rows are not locked, but the rejection is still logged with the reason.

## Scope categorization

The app assigns scope during import.

### SAP

SAP rows are split into fuel and procurement based on material text.

Fuel-like rows become:

```text
activity_type = fuel
scope = scope_1
```

Other SAP rows become:

```text
activity_type = procurement
scope = scope_3
```

Fuel keywords include terms like diesel, petrol, gasoline, fuel, LPG, natural gas, and CNG.

This is a practical shortcut for the prototype. In a real SAP setup, I would prefer material groups, GL accounts, purchasing categories, or a customer-specific mapping table.

### Utility electricity

Utility electricity rows become:

```text
activity_type = electricity
scope = scope_2
```

Purchased electricity is treated as Scope 2 activity data.

### Corporate travel

Travel rows become:

```text
scope = scope_3
```

Supported activity types:

- flight
- hotel
- ground_transport

Business travel is an indirect company activity, so I treated it as Scope 3.

## Unit normalization

The model stores both original and normalized values.

Example utility row:

```text
quantity_original = 52.4
unit_original = MWh
quantity_normalized = 52400
unit_normalized = kWh
```

I kept both because the original value is useful for traceability, while the normalized value is useful for review and later calculations.

Current normalization examples:

- MWh to kWh
- gallons to liters
- tonnes to kg
- liters stay liters
- kg stays kg

Unknown units are preserved and flagged instead of silently converted.

## Review states

Current statuses:

```text
valid
suspicious
invalid
approved
rejected
```

The frontend also shows a review label:

```text
approved/rejected -> Already reviewed
valid/suspicious  -> Needs review
invalid           -> Needs decision
```

Approved rows are locked because they are considered audit-ready. Rejected rows stay unlocked because they are not being used as approved evidence.

## What I would improve next

If this moved toward production, I would add:

- real authentication
- tenant membership and permissions
- original file storage, probably S3
- background jobs for large uploads
- duplicate detection using raw hashes
- better SAP classification through mapping tables
- emissions factor models after approval
- stronger edit history if analysts are allowed to manually edit normalized fields
