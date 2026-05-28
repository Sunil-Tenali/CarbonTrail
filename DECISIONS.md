# DECISIONS.md

This file explains the main choices I made for the backend prototype. I tried to keep the project small enough to understand, but still close to the assignment problem: messy enterprise data that needs to be normalized and reviewed before audit.

## Current backend scope

The backend currently handles:

- CSV upload for SAP fuel/procurement data
- CSV upload for utility electricity data
- CSV upload for corporate travel data
- raw row preservation
- normalized `ActivityRecord` creation
- validation issues
- approval and rejection workflow
- locking approved rows
- audit logs for imports and analyst actions
- SQLite locally, with PostgreSQL support through `DATABASE_URL`

The frontend is not covered in this backend-only pass. It will be added later.

## Why I used file upload for all three sources

The assignment allowed choosing the ingestion mechanism. I chose CSV upload for this prototype because it is realistic for a 4-day onboarding prototype.

In a real enterprise setup, SAP, utilities, and travel platforms could be connected through APIs, scheduled jobs, SFTP, or middleware. But for a prototype, requiring real credentials for SAP, utility portals, or Concur/Navan would slow the work down and make the demo harder to run.

CSV upload keeps the focus on the harder part of the assignment: preserving messy source data, normalizing it, flagging bad rows, and giving analysts a review workflow.

## SAP decision

### What I chose

I handled SAP as a flat CSV export for fuel and procurement-like rows.

The importer accepts common SAP-style column names such as:

- `Document Number`
- `Posting Date`
- `Plant`
- `Material`
- `Quantity`
- `UoM`
- `Amount`
- `Currency`

It also supports some alternate names like German column names (`Werk`, `Buchungsdatum`, `Belegnummer`) because SAP exports are often customized.

### Why

SAP can expose data in many ways: IDocs, BAPIs, OData services, flat files, and custom reports. For this prototype, a flat file is easier to demo and still realistic because many teams export SAP reports into CSV during onboarding.

The importer keeps the subset small:

- material/document rows only
- plant/facility code tracking
- mixed date parsing
- basic unit normalization
- simple classification into fuel or procurement

### How Scope is assigned

- If the material text contains words like `diesel`, `petrol`, `fuel`, `lpg`, `natural gas`, or `cng`, the row is treated as fuel and assigned `scope_1`.
- Otherwise, the row is treated as procurement and assigned `scope_3`.

This is simple, but defendable for a prototype. In production I would not rely only on keyword matching. I would use material master data, GL accounts, purchasing categories, or a mapping table maintained by the sustainability/finance team.

## Utility electricity decision

### What I chose

I handled utility data as a portal-style electricity CSV export.

The expected fields are close to what a facilities team might export:

- `meter_id`
- `facility_code`
- `billing_period_start`
- `billing_period_end`
- `usage_quantity`
- `usage_unit`
- `demand_kw`
- `tariff_name`
- `amount`
- `currency`

### Why

The assignment mentions PDF bills, portal scrapes, and utility APIs. I chose portal CSV because PDF parsing/OCR would become a separate project by itself, and utility APIs are not available everywhere.

A billing-period CSV still captures the important utility problems:

- meters belong to facilities
- billing periods do not always match calendar months
- units may be kWh or MWh
- some rows can have missing meters or invalid date ranges

### How Scope is assigned

All utility electricity rows are assigned `scope_2`, because purchased electricity is Scope 2 activity data.

### Unit handling

The importer normalizes:

- `kWh` to `kWh`
- `MWh` to `kWh` by multiplying by 1000

Unsupported units are flagged as validation errors.

## Corporate travel decision

### What I chose

I handled travel as a Concur/Navan-style travel CSV with three categories:

- `flight`
- `hotel`
- `ground_transport`

The importer supports fields such as:

- `trip_id`
- `employee_id`
- `category`
- `booking_date`
- `start_date`
- `end_date`
- `origin_airport`
- `destination_airport`
- `distance_km`
- `hotel_nights`
- `ground_transport_mode`
- `amount`
- `currency`

### Why

Travel platforms usually have booking, itinerary, and expense information, but the exact field names vary by customer setup. I kept the importer focused on one clean CSV shape that still represents realistic categories.

### How Scope is assigned

All travel rows are assigned `scope_3`, because business travel is an indirect emissions category.

### Validation choices

The importer checks different fields depending on the category:

- flights need airport codes and distance
- hotels need number of nights
- ground transport needs a recognizable mode

This lets the backend catch category-specific problems without building a full travel calculation engine.

## Raw row and normalized record decision

I split source data into two layers:

1. `RawActivityRow` keeps the original CSV row as JSON.
2. `ActivityRecord` stores the normalized version analysts review.

I did this because the raw row is the source evidence. If an analyst asks, “What exactly came from SAP or the utility file?”, the raw payload is still available.

The normalized row is allowed to have cleaner fields like `scope`, `activity_type`, `quantity_normalized`, and `unit_normalized`.

## Approval and locking decision

Only `valid` and `suspicious` unlocked records can be approved. Once approved, the row becomes locked.

I chose this because the assignment specifically says analysts should approve rows before they are locked for audit. A locked row should not be edited later because that would weaken the audit trail.

Rejected rows are not locked. My thinking is that rejected rows may need to be replaced or re-uploaded with better source data.

## Validation issue decision

I used separate `ValidationIssue` rows instead of putting one error message directly on `ActivityRecord`.

That gives more flexibility because a single imported row can have multiple problems. For example, a utility row might have both a missing meter ID and an invalid billing period.

I used two severities:

- `error`: row is invalid
- `warning`: row is suspicious but can still be reviewed

## Authentication decision

The API currently uses `AllowAny` because the focus was ingestion and review workflow, not user authentication.

This is not production-ready security. Before deployment for real users, I would add authentication and tenant-based access checks so users can only see their own organization’s data.

## Database decision

Local development uses SQLite because it is quick and easy to run.

Deployment should use PostgreSQL through `DATABASE_URL`. The settings file supports this, so the same code can use SQLite locally and PostgreSQL on Render/Railway/Fly.

## What I ignored for now

I deliberately did not build:

- real SAP API connection
- real utility portal scrape or PDF OCR
- real Concur/Navan OAuth integration
- emissions-factor calculations
- tenant-specific source mapping UI
- user roles and permissions
- frontend dashboard in this backend-only pass

## Questions I would ask the PM

1. Which SAP export should we standardize on for the first client: custom report, OData, IDoc, or manual CSV?
2. Does the client already have plant-to-facility mapping somewhere?
3. For procurement, do we need category mapping from GL accounts, material groups, or vendor types?
4. For electricity, do we receive one meter per facility or multiple meters per facility?
5. Do utility billing periods need to be split into calendar months for reporting?
6. For travel, should missing flight distance be calculated from airport codes or flagged for analyst review?
7. Should analysts be allowed to edit normalized rows, or only approve/reject them?
8. After approval, who is allowed to unlock a row if a mistake is found?
9. Are we expected to calculate CO2e in this prototype, or only normalize activity data?
10. What deployment provider and database should be used for final submission?
