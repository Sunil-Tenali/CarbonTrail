# CarbonTrail Backend

CarbonTrail is a backend prototype for the Breathe ESG tech intern assignment.

The goal is to ingest messy activity data from different enterprise sources, normalize it, and let an analyst review the rows before they are locked for audit.

This ZIP/documentation pass is backend-only. The React frontend will be added later.

## What the backend does

The Django REST backend supports three upload types:

1. SAP fuel/procurement CSV
2. Utility electricity CSV
3. Corporate travel CSV

For each uploaded CSV, the backend:

- creates an import batch
- saves every original CSV row as raw JSON
- creates a normalized activity record
- assigns Scope 1, 2, or 3
- normalizes units where supported
- creates validation issues for bad or suspicious rows
- allows analysts to approve or reject rows
- locks approved rows
- writes audit logs for imports and analyst actions

## What is not done yet

This backend does not currently include:

- React frontend dashboard
- deployed live URL
- real login/tenant permissions
- real SAP, utility, Concur, or Navan integrations
- PDF bill OCR
- CO2e emissions-factor calculations
- production file storage for uploaded CSV files

The backend has deployment-oriented settings, but deployment itself still needs to be done.

## Tech stack

- Python
- Django
- Django REST Framework
- SQLite for local development
- PostgreSQL support through `DATABASE_URL`
- WhiteNoise for static files during deployment
- Gunicorn for production serving

## Project structure

```text
backend/
  activities/      Normalized activity records, validation issues, review workflow
  audit/           Audit logs for imports and analyst actions
  config/          Django settings and URLs
  ingestion/       Source systems, import batches, raw rows, CSV importers
  organizations/   Tenant model for multi-tenancy
  manage.py
```

## Main API endpoints

```text
GET  /api/source-systems/
GET  /api/import-batches/
POST /api/ingestion/upload/
GET  /api/activity-records/
GET  /api/activity-records/{id}/
GET  /api/activity-records/summary/
POST /api/activity-records/{id}/approve/
POST /api/activity-records/{id}/reject/
GET  /api/audit-logs/
```

## Local setup

From the backend folder:

```powershell
cd backend
```

Create and activate a virtual environment if needed:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Install dependencies.

If `requirements.txt` exists:

```powershell
pip install -r requirements.txt
```

If it has not been generated yet, install the needed packages manually:

```powershell
uv pip install Django djangorestframework django-cors-headers gunicorn whitenoise dj-database-url "psycopg[binary]"
```

Then create `requirements.txt` before submission:

```powershell
uv pip freeze > requirements.txt
```

## Environment variables

Copy the example env file:

```powershell
copy .env.example .env
```

For local development, SQLite is used automatically if `DATABASE_URL` is not set.

Important variables:

```text
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DATABASE_URL=
```

For deployment, set `DATABASE_URL` to a PostgreSQL URL from Render, Railway, Fly, or another provider.

## Database setup

Run migrations:

```powershell
uv run python manage.py makemigrations
uv run python manage.py migrate
```

Create an admin user:

```powershell
uv run python manage.py createsuperuser
```

Start the server:

```powershell
uv run python manage.py runserver
```

Open admin:

```text
http://127.0.0.1:8000/admin/
```

Create a `Tenant` in admin before uploading files. Example:

```text
Acme Manufacturing
```

Use that tenant ID in upload requests.

## Upload examples

The backend expects sample data files at the repo root under `sample_data/`.

From the `backend` folder, the paths look like this:

```text
../sample_data/sap_fuel_procurement_sample.csv
../sample_data/utility_electricity_sample.csv
../sample_data/travel_sample.csv
```

The backend ZIP I inspected does not include the `sample_data` folder, so make sure the root project has those files before demoing.

## Upload utility electricity

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/ingestion/upload/ `
  -F "tenant_id=1" `
  -F "source_type=utility" `
  -F "file=@../sample_data/utility_electricity_sample.csv"
```

## Upload travel

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/ingestion/upload/ `
  -F "tenant_id=1" `
  -F "source_type=travel" `
  -F "file=@../sample_data/travel_sample.csv"
```

## Upload SAP

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/ingestion/upload/ `
  -F "tenant_id=1" `
  -F "source_type=sap" `
  -F "file=@../sample_data/sap_fuel_procurement_sample.csv"
```

## Check imported rows

Open:

```text
http://127.0.0.1:8000/api/activity-records/
```

Or use Django shell:

```powershell
uv run python manage.py shell
```

```python
from activities.models import ActivityRecord

for r in ActivityRecord.objects.all().order_by("id"):
    print(r.id, r.source_type, r.activity_type, r.scope, r.status, r.source_reference)
```

Expected scope behavior:

```text
SAP fuel rows        -> scope_1
SAP procurement rows -> scope_3
Utility electricity  -> scope_2
Travel rows          -> scope_3
```

## Approve and reject rows

Only `valid` and `suspicious` unlocked rows can be approved.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/activity-records/38/approve/
```

Reject a row using PowerShell:

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/activity-records/36/reject/" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"reason":"Rejected during test review"}'
```

Check audit logs:

```text
http://127.0.0.1:8000/api/audit-logs/
```

## Tests

Run:

```powershell
uv run python manage.py test
```

Current tests cover:

- SAP import creates raw and normalized rows
- utility MWh converts to kWh
- invalid utility billing period is flagged
- missing flight distance is flagged
- missing hotel nights is flagged
- raw rows are preserved
- import audit log is created
- approval locks a row
- locked rows cannot be edited
- rejection creates audit log

## Deployment notes

The backend settings support deployment, but deployment still needs to be completed.

For Render/Railway/Fly style deployment:

1. Use PostgreSQL and set `DATABASE_URL`.
2. Set `SECRET_KEY` to a real secret.
3. Set `DEBUG=False`.
4. Set `ALLOWED_HOSTS` to the backend domain.
5. Set `CORS_ALLOWED_ORIGINS` to the frontend domain when frontend is ready.
6. Run migrations on deploy.
7. Use Gunicorn as the start command.

Example start command:

```bash
gunicorn config.wsgi:application
```

Example build/start steps depend on the provider and should be finalized during deployment.

## Live URL and credentials

```text
Live backend URL: TODO after deployment
Frontend URL: TODO after frontend deployment
Demo credentials: TODO after auth/demo setup
```

## Current limitations

- Authentication is not production-ready. API views currently allow open access for development.
- Tenant isolation exists in the data model, but request-level tenant permission checks still need to be added.
- There is no real emissions calculation engine yet.
- Importers handle a practical subset of CSV formats, not every real SAP/utility/travel variation.
- Sample CSV files need to be kept in the root `sample_data/` folder for demo uploads.
- Deployment has not been verified from this backend ZIP.
