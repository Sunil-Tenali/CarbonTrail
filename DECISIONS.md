# DECISIONS.md

This file explains the choices I made while building CarbonTrail. I tried to keep the prototype realistic but still small enough to finish and defend.

## 1. I used CSV upload for all three sources

I chose CSV upload for SAP, utility electricity, and travel.

The assignment allowed different ingestion mechanisms. I picked CSV because it is realistic for onboarding and easy to test in a demo. A lot of enterprise work starts with exported files before API access is ready.

I did not choose live APIs because SAP, utility portals, Concur, or Navan would all need credentials and customer-specific setup. That would make the prototype harder to run and review.

The current upload endpoint is:

```text
POST /api/ingestion/upload/
```

The frontend sends:

```text
tenant_id
source_type
file
```

`source_type` decides which importer runs.

## 2. I chose a flat SAP CSV export

SAP can expose data in several ways: IDocs, OData APIs, BAPIs, reports, and flat files. For this prototype I chose a flat CSV export that looks like a material/procurement movement report.

The importer handles fields like:

- document number
- posting date
- plant/facility
- material description
- quantity
- unit of measure
- amount
- currency

I also allowed some alternate column names, including German-style SAP labels like `Werk` and `Buchungsdatum`.

I ignored IDocs, direct SAP OData pulls, and full material master lookups because those would require a much larger setup.

## 3. I used keyword classification for SAP fuel vs procurement

SAP fuel rows are classified using material text. If the material contains words like diesel, fuel, petrol, LPG, natural gas, or CNG, the row is treated as fuel.

That becomes:

```text
fuel -> Scope 1
```

Everything else becomes procurement:

```text
procurement -> Scope 3
```

This is not production-grade, but it is understandable for a prototype. In a real client setup, I would ask for material groups, GL accounts, purchasing categories, or a mapping table.

## 4. I chose utility portal CSV instead of PDF bills

Utility bills often arrive as PDFs, but PDF extraction is messy. The same field can appear in different layouts, pages, and table formats. OCR can also misread numbers.

For this prototype I chose a utility portal CSV export. That still lets the app handle realistic utility problems:

- meter IDs
- billing periods
- kWh and MWh
- demand kW
- tariff names
- invalid date ranges
- missing meters
- unusually high usage

I did not build PDF OCR because it would take time away from the main data model and review workflow.

## 5. I treated electricity as Scope 2

Utility electricity rows are always imported as:

```text
activity_type = electricity
scope = scope_2
```

That matches the usual treatment of purchased electricity as Scope 2 activity data.

## 6. I chose travel platform CSV for flights, hotels, and ground transport

For corporate travel, I modeled the source as a Concur/Navan-style CSV export.

The importer supports:

- flights
- hotels
- ground transport

Flights use airport codes and distance when available. Hotels use nights. Ground transport uses mode and distance.

All travel rows are treated as Scope 3 because business travel is an indirect company activity.

## 7. I preserved raw rows separately from normalized rows

This was one of the most important choices.

The raw CSV row is stored in `RawActivityRow`. The cleaned review row is stored in `ActivityRecord`.

That means analysts can review the normalized row without losing the original source evidence. It also makes debugging easier when a number looks wrong.

## 8. I used validation issues instead of only one status field

A row can have more than one problem. For example, a utility row could have a missing meter ID and an unsupported unit.

So I used a separate `ValidationIssue` model.

The row status is based on those issues:

```text
error issue    -> invalid
warning issue  -> suspicious
no issue       -> valid
```

This gives the frontend enough detail to show what failed and why.

## 9. Approved rows are locked

When an analyst approves a row, the backend sets:

```text
status = approved
is_locked = true
```

The row cannot be edited after that. I did this because approval means the row is now audit-ready, and changing it later without a new workflow would be risky.

Rejected rows are not locked. They are marked rejected and an audit log is created with the rejection reason.

## 10. I kept authentication simple for the prototype

The current API uses permissive access. That made the app easier to test and demo.

For production, this would need to change. I would add:

- login
- tenant membership
- analyst/admin roles
- request-level tenant filtering
- proper DRF permissions

The data model already has tenant ownership, but permissions are not complete yet.

## 11. I used SQLite locally and PostgreSQL for deployment

SQLite is simple for local development.

For deployment, the app reads `DATABASE_URL`. If that variable is set, Django uses PostgreSQL through `dj-database-url` and `psycopg`.

So the same code can run locally and on Render/Railway:

```text
local without DATABASE_URL -> SQLite
production with DATABASE_URL -> PostgreSQL
```

## Questions I would ask the PM

If this were a real onboarding project, I would ask:

1. Do we expect file uploads only, or do we need SAP/Concur/utility API pulls?
2. What SAP fields does the client actually export?
3. Do they have material groups or GL account mappings for fuel/procurement classification?
4. Are plant codes already mapped to facilities?
5. Should utility billing periods be allocated into calendar months?
6. Do we need to store original uploaded files, not just row payloads?
7. Should rejected rows be editable and resubmitted?
8. Who is allowed to approve rows?
9. Do auditors need a downloadable evidence package?
10. Should emissions factors be added now or after activity data approval?
