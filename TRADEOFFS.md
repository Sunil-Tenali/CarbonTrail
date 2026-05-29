# TRADEOFFS.md

This file lists the main things I deliberately did not build. I am including more than three because a few of these were conscious cuts while keeping the prototype focused.

## 1. I did not build PDF utility bill OCR

I chose utility CSV upload instead of PDF bill extraction.

PDF bills are realistic, but they are a separate problem. Every utility formats bills differently, and OCR can easily misread meter numbers, dates, or usage values. Building this well would need visual review, parsing rules, and a way to store the original PDF evidence.

For this prototype, I wanted to handle the core electricity data shape first:

- meter ID
- usage quantity
- units
- billing period
- tariff name
- amount

A later version could add PDF bill upload as a separate importer while keeping the CSV path as the cleaner fallback.

## 2. I did not connect to real SAP, utility, Concur, or Navan APIs

The app uses file upload instead of live integrations.

This is a tradeoff. Real enterprise onboarding often needs APIs, SFTP drops, or middleware. But real integrations would need credentials, sandbox access, custom field mappings, and sometimes customer-specific configuration.

CSV upload keeps the demo runnable and still shows the important logic:

- source routing
- raw row preservation
- normalization
- validation
- review workflow
- audit logs

In production, I would keep the importer classes but add API adapters around them.

## 3. I did not calculate final CO2e emissions

The app stops at normalized activity data.

It does not apply emissions factors or calculate final tonnes of CO2e. I made this choice because the assignment emphasized ingestion and normalization. Emissions calculation is important, but it brings another set of models and rules:

- factor source
- factor version
- region
- activity date validity
- unit compatibility
- market-based vs location-based electricity
- audit trail for factor changes

I would add emissions calculation after the activity rows are approved.

## 4. SAP classification is simple

SAP fuel vs procurement classification is currently based on keywords in the material description.

That is enough for clear demo rows like diesel or LPG, but it is not enough for a real SAP customer.

A better production version would use:

- material groups
- GL accounts
- purchasing categories
- vendor categories
- plant/facility mappings
- customer-specific rules

I kept the current approach because it is easy to explain and enough to show the workflow.

## 5. I did not build full authentication and role permissions

The prototype endpoints are open so the app is easy to run and test.

That is not safe for real customer data. Before production, I would add:

- user login
- tenant membership
- analyst/admin roles
- per-tenant query restrictions
- permissions around approve/reject actions

The data model already supports tenant ownership, but access control needs to be added at the API layer.

## 6. I did not add background jobs for large imports

Imports currently run inside the HTTP request.

That is okay for small sample CSVs, but a real enterprise file could have thousands or millions of rows. In that case, the app should use Celery, RQ, or another job queue.

A better production flow would be:

1. Upload file.
2. Create batch with `processing` status.
3. Process rows in a background job.
4. Show progress and errors in the UI.

I kept synchronous imports because they are easier to debug and enough for a prototype.

## 7. I did not store the original uploaded CSV file

The app stores every raw row as JSON, but it does not store the original uploaded file in object storage.

For audit, row-level raw payloads are helpful. But a real system should also store the exact original file in S3 or similar storage so the auditor can download it later.

## 8. I did not build manual row editing

Analysts can approve or reject rows, but they cannot edit normalized values in the frontend.

This was intentional. Editing emissions activity data needs a stronger audit trail. If analysts can change values, the app should store before/after diffs, editor identity, reason codes, and maybe require re-approval.

For this prototype, reject-and-resubmit is safer than silent editing.

## 9. I kept the UI simple

The React frontend is intentionally plain. It focuses on the review workflow instead of polished design.

The important screens are there:

- dashboard
- upload page
- import batches
- activity review table
- row detail
- audit logs

If I had more time, I would improve table pagination, search, sorting, loading states, and empty-state design.
