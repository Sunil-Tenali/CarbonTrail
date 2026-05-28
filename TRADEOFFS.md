# TRADEOFFS.md

This file lists the main things I deliberately did not build. I tried to keep the backend realistic for a short prototype instead of building a wide but shallow app.

## 1. No PDF utility bill OCR

The assignment mentions utility bills as PDFs or portal exports. I chose portal-style CSV upload.

PDF bill OCR is a whole separate problem:

- every utility formats bills differently
- tables can be split across pages
- OCR can misread numbers
- charges and usage are often mixed together
- validation would need visual evidence from the bill

For this prototype, CSV still lets me handle the important utility data problems: meters, billing periods, kWh/MWh, demand, tariffs, invalid dates, and missing meter IDs.

If I had more time, I would add PDF upload as a separate ingestion path and keep the current CSV importer as the cleaner fallback.

## 2. No real SAP, Concur, Navan, or utility API integrations

I used CSV upload instead of live API integrations.

This is a tradeoff because real enterprise onboarding often needs APIs, SFTP, or middleware. But connecting to real systems requires credentials, customer-specific setup, and provider-specific configuration.

For a 4-day prototype, CSV upload is easier to run and review. It still shows the important backend logic:

- source type routing
- raw row preservation
- normalization
- validation issues
- approval workflow
- audit logging

In production, I would probably keep the importer classes but add separate ingestion adapters for SAP OData/BAPI, utility APIs, and Concur/Navan APIs.

## 3. No full CO2e emissions calculation engine

The backend does not calculate final emissions in CO2e.

It stops at normalized activity data:

- liters or kg for SAP fuel/procurement
- kWh for electricity
- km or nights for travel

I made this choice because the assignment says the hard part is data ingestion and normalization, not just carbon calculation. Emissions factors would need their own model, versioning, region support, date validity, unit compatibility, and audit trail.

For production, I would add an emissions factor layer after activity records are approved.

## 4. Simple SAP classification

SAP fuel vs procurement classification is currently based on keywords in the material description.

This is not enough for a real customer. Real classification should use:

- material groups
- GL accounts
- purchasing categories
- vendor categories
- plant/facility mappings
- customer-specific rules

I kept keyword classification because it is easy to understand in a demo and works for clear sample rows like diesel or LPG. I documented this because I would not want to pretend it is production-grade.

## 5. No real authentication or role-based permissions yet

The API currently uses permissive access for development.

That made it faster to test uploads, approval, rejection, and audit logs. But it is not safe for production.

Before using this with real company data, I would add:

- login
- tenant membership
- analyst/admin roles
- per-tenant query restrictions
- proper API permissions

The data model already has tenant foreign keys, but request-level access control still needs to be added.

## 6. No background processing for large files

Imports currently run during the HTTP request.

That is fine for small demo CSVs, but not for large enterprise files. A production version should use a background job system like Celery/RQ and show processing progress in the UI.

I kept synchronous import because it is easier to debug and enough for the assignment prototype.

## 7. No original file storage

The backend stores every row as JSON, but it does not store the uploaded CSV file itself in object storage.

For audit, row-level raw payloads are useful. But in production, I would also store the exact original file in S3 or another storage system so auditors can download the original evidence.

## 8. No frontend yet in this backend pass

The assignment requires a React review dashboard, but this current pass is backend-only.

The backend APIs are shaped so the frontend can later show:

- upload summary
- import batches
- activity review table
- validation issues
- raw payload
- audit history
- approve/reject actions

I am not claiming the frontend is done in these docs.
