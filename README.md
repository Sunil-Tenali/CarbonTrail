# CarbonTrail

CarbonTrail is my prototype for the Breathe ESG tech intern assignment. It is a Django REST + React app for taking messy company activity data, normalizing it, and giving an analyst a place to review the rows before they are treated as audit-ready.

The app handles three source types:

- SAP fuel and procurement CSV exports
- Utility electricity CSV exports
- Corporate travel CSV exports

The main thing I focused on was not carbon calculation. I focused on the part of the assignment called out as hard: different source shapes, missing fields, inconsistent units, review status, and audit traceability.

## Current status

The prototype currently includes:

- Django REST backend
- React frontend dashboard
- Company/tenant creation from the frontend
- CSV upload for SAP, utility electricity, and travel
- Import batch tracking
- Raw row preservation
- Normalized activity records
- Scope 1 / Scope 2 / Scope 3 classification
- Validation issues for invalid or suspicious rows
- Analyst approves/rejects actions
- Approved rows locked for audit
- Rejected rows tracked with a reason
- Audit logs for imports, approvals, and rejections
- Local SQLite support
- PostgreSQL support in deployment through `DATABASE_URL.`

## Live URLs

Frontend URL: https://carbontrail-frontend.onrender.com  
Backend API URL: https://carbontrail-backend.onrender.com/api/
Demo credentials: Not required for this prototype. The current endpoints are open for demo purposes.

The deployed database starts empty. For a clean demo, create a company from the Upload page and upload the three sample CSV files again.

## Tech stack

Backend:

- Python
- Django
- Django REST Framework
- SQLite locally
- PostgreSQL in deployment through `DATABASE_URL`
- Gunicorn
- WhiteNoise
- django-cors-headers

Frontend:

- React
- Create React App
- React Router
- CSS in `App.css`

Deployment:

- Render Web Service for the backend
- Render PostgreSQL for the production database
- Render Static Site for the frontend

## Project structure

```text
CarbonTrail/
  backend/
    activities/        Activity records, validation issues, review actions
    audit/             Audit log model and API
    config/            Django settings and root URLs
    ingestion/         Import batches, raw rows, source systems, CSV importers
    organizations/     Company/tenant model and API
    manage.py

  frontend/
    src/
      api.js
      App.js
      App.css
      pages/
        DashboardPage.js
        UploadPage.js
        BatchesPage.js
        RecordsPage.js
        RecordDetailPage.js
        AuditLogsPage.js

  sample_data/
    sap_fuel_procurement_sample.csv
    utility_electricity_sample.csv
    travel_sample.csv

  README.md
  MODEL.md
  DECISIONS.md
  TRADEOFFS.md
  SOURCES.md
```

## Backend setup

From the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r ..\requirements.txt
python manage.py migrate
python manage.py runserver
```

The backend runs at:

```text
http://127.0.0.1:8000
```

Useful API endpoints:

```text
GET  /api/tenants/
POST /api/tenants/
GET  /api/import-batches/
POST /api/ingestion/upload/
GET  /api/activity-records/
GET  /api/activity-records/{id}/
POST /api/activity-records/{id}/approve/
POST /api/activity-records/{id}/reject/
GET  /api/audit-logs/
```

## Frontend setup

In a second terminal:

```powershell
cd frontend
npm install
npm start
```

The frontend runs at:

```text
http://localhost:3000
```

For local development, `frontend/.env` should contain:

```env
REACT_APP_API_BASE_URL=http://127.0.0.1:8000/api
```

Do not commit `frontend/.env`. Commit `frontend/.env.example` instead.

## How to demo locally

1. Start the backend.
2. Start the frontend.
3. Open `http://localhost:3000`.
4. Go to Upload CSV.
5. Add a company, for example `Acme Manufacturing`.
6. Upload the utility sample as `Utility electricity`.
7. Upload the travel sample as `Corporate travel`.
8. Upload the SAP sample as `SAP fuel/procurement`.
9. Go to Import Batches and check row counts.
10. Go to Activity Review and filter by company, source, scope, status, or issue state.
11. Open a row detail page.
12. Approve one valid or suspicious row.
13. Reject one row with a reason.
14. Go to Audit Logs and confirm imported, approved, and rejected events are visible.

## How to demo the live app

1. Open the frontend URL.
2. Go to Upload CSV.
3. Add a company, for example `Acme Manufacturing`.
4. Upload `utility_electricity_sample.csv` as Utility electricity.
5. Upload `travel_sample.csv` as Corporate travel.
6. Upload `sap_fuel_procurement_sample.csv` as SAP fuel/procurement.
7. Open Dashboard and check the counts.
8. Open Import Batches and confirm the company, source, and file rows.
9. Open Activity Review and filter by source, scope, status, or issue state.
10. Open a row detail page.
11. Approve one valid or suspicious row.
12. Reject one row with a reason.
13. Open Audit Logs and confirm imported, approved, and rejected events are visible.

## Upload API example

From the `backend` folder:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/ingestion/upload/ `
  -F "tenant_id=1" `
  -F "source_type=utility" `
  -F "file=@../sample_data/utility_electricity_sample.csv"
```

`source_type` must be one of:

```text
sap
utility
travel
```

The selected `source_type` decides which importer reads the file. For example, a utility CSV should be uploaded as `utility`. If the wrong file is uploaded under the wrong source type, the importer may reject it or create validation issues because the expected columns are missing.

## Tests and checks

Backend:

```powershell
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Frontend:

```powershell
cd frontend
npm run build
```

These are the checks I run before calling the project ready to deploy.

## Deployment notes

The backend is prepared to use SQLite locally and PostgreSQL in deployment. The switch happens through `DATABASE_URL`.

If `DATABASE_URL` is not set, Django uses local SQLite:

```text
backend/db.sqlite3
```

If `DATABASE_URL` is set, Django uses PostgreSQL through `dj-database-url` and `psycopg`.

Recommended deployment setup:

- Backend: Render Web Service
- Database: Render PostgreSQL
- Frontend: Render Static Site

Backend build command:

```bash
pip install -r requirements.txt && cd backend && python manage.py collectstatic --noinput && python manage.py migrate
```

Backend start command:

```bash
cd backend && gunicorn config.wsgi:application
```

Frontend build command:

```bash
npm install && npm run build
```

Frontend publish directory:

```text
build
```

Backend environment variables for deployment:

```env
SECRET_KEY=replace-with-real-secret
DEBUG=False
ALLOWED_HOSTS=your-backend-domain.onrender.com
DATABASE_URL=postgresql://...
CORS_ALLOWED_ORIGINS=https://carbontrail-frontend.onrender.com
CORS_ALLOW_ALL_ORIGINS=False
```

Frontend environment variable for deployment:

```env
REACT_APP_API_BASE_URL=https://your-backend-domain.onrender.com/api
```

For the deployed frontend, this value must point to the deployed backend, not localhost.

## Resetting demo data

For local development, imported records can be cleared from the Django shell if the demo data becomes messy.

For deployment, the live PostgreSQL database starts empty. The easiest clean demo flow is to create a company from the frontend and upload the three sample CSV files again.

## Known limitations

This is still a prototype. It does not include real authentication, role-based permissions, live SAP/Concur/utility API integrations, PDF bill OCR, emissions factor calculations, or background jobs for large files.

The app currently focuses on the data ingestion, normalization, validation, review, and audit trail workflow. More production-level tradeoffs are explained in `TRADEOFFS.md`.
