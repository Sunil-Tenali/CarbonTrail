# CarbonTrail Backend Architecture Guide

**For Interview Preparation:** A comprehensive guide to the CarbonTrail backend system for quick reference and explanation.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Key Files & Structure](#key-files--structure)
4. [Data Flow](#data-flow)
5. [Core Modules](#core-modules)
6. [API Endpoints](#api-endpoints)
7. [Database Models](#database-models)
8. [Key Design Patterns](#key-design-patterns)
9. [Interview Talking Points](#interview-talking-points)

---

## Project Overview

**CarbonTrail** is a Django REST Framework application that manages emissions data for organizations.

### Purpose
- Import emissions data from multiple sources (SAP, utility companies, travel platforms)
- Validate and classify data according to GHG Protocol standards
- Provide approval workflow for compliance
- Maintain immutable audit trail for regulatory compliance

### Technology Stack
- **Backend:** Django 6.0.5 (Python web framework)
- **API:** Django REST Framework (for JSON REST endpoints)
- **Database:** SQLite (development) / PostgreSQL (production ready)
- **Middleware:** CORS for frontend access, session management, CSRF protection
- **Architecture:** Multi-tenant SaaS (each organization isolated)

---

## Architecture

### Multi-Tenancy Design
```
Every model has tenant_id ForeignKey:
- ActivityRecord.tenant
- RawActivityRow.tenant
- ImportBatch.tenant
- AuditLog.tenant

Result: Complete data isolation per customer
```

### Layered Architecture
```
HTTP Request
    ↓
URL Router (config/urls.py)
    ↓
ViewSet (activities/views.py)
    ↓
Serializer (activities/serializers.py)
    ↓
Model (activities/models.py)
    ↓
Database (db.sqlite3)
    ↓
JSON Response
```

### Request Processing Pipeline
```
1. Middleware processes request (CORS, sessions, auth)
2. URL router matches endpoint
3. ViewSet method handles HTTP method (GET/POST/PATCH)
4. Serializer validates and transforms data
5. Model queries/saves data
6. Response serialized back to JSON
```

---

## Key Files & Structure

### Configuration Files (`config/`)
| File | Purpose |
|------|---------|
| `settings.py` | Project configuration, installed apps, middleware, database, security settings |
| `urls.py` | Main URL routing - maps HTTP paths to views |
| `wsgi.py` | Web Server Gateway Interface - entry point for production servers |
| `asgi.py` | Async ASGI - entry point for async servers (WebSockets, real-time) |

### Activities App (`activities/`)
| File | Purpose |
|------|---------|
| `models.py` | ActivityRecord, ValidationIssue - core emissions data model |
| `views.py` | ActivityRecordViewSet - REST endpoints for CRUD + approve/reject |
| `serializers.py` | Convert models to JSON, validate input |
| `admin.py` | Django admin interface for staff |
| `urls.py` | Routes for /api/activity-records/ endpoints |

### Organizations App (`organizations/`)
| File | Purpose |
|------|---------|
| `models.py` | Tenant - represents customer organization |
| `admin.py` | Create/manage organizations in admin |
| `views.py` | (Empty) Future: API for org management |

### Ingestion App (`ingestion/`)
| File | Purpose |
|------|---------|
| `models.py` | SourceSystem, ImportBatch, RawActivityRow - data import models |
| `admin.py` | Monitor imports, inspect raw data, track validation stats |
| `views.py` | (Empty) Future: File upload endpoints |

### Audit App (`audit/`)
| File | Purpose |
|------|---------|
| `models.py` | AuditLog - tracks all significant changes |
| `admin.py` | View all user actions and changes |
| `views.py` | (Empty) Future: Compliance report endpoints |

---

## Data Flow

### Complete Emissions Data Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 1: DATA IMPORT                         │
├─────────────────────────────────────────────────────────────────┤
│ User uploads CSV file (e.g., from SAP, utility company)        │
│ → ImportBatch created (status="processing")                    │
│ → Each row → RawActivityRow (immutable copy of data)           │
│ → Validation rules applied                                     │
│ → ValidationIssue records created for problems                 │
│ → RawActivityRow linked to ActivityRecord                      │
│ → ImportBatch status → "completed"                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   STEP 2: INITIAL VALIDATION                    │
├─────────────────────────────────────────────────────────────────┤
│ ActivityRecord status assigned:                                │
│ • "valid" - Passed all checks                                 │
│ • "suspicious" - Has warnings, needs review                   │
│ • "invalid" - Critical errors, cannot use                     │
│                                                               │
│ ValidationIssue.severity:                                      │
│ • "error" - Critical (missing facility, invalid scope)        │
│ • "warning" - Informational (outliers, future dates)          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                 STEP 3: ANALYST REVIEW                          │
├─────────────────────────────────────────────────────────────────┤
│ Analyst views records in UI                                    │
│ Filters by: status, source, organization                      │
│ Reviews validation issues                                      │
│ Corrects data if needed (edit quantity, facility code, etc.)  │
│ When locked: prevents further edits                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              STEP 4: APPROVAL WORKFLOW                          │
├─────────────────────────────────────────────────────────────────┤
│ APPROVE:                                                        │
│ → Record status = "approved"                                   │
│ → is_locked = True (compliance protection)                    │
│ → approved_by, approved_at captured                            │
│ → AuditLog created (before/after snapshots)                    │
│ → Now ready for reports                                        │
│                                                               │
│ REJECT:                                                        │
│ → Record status = "rejected"                                   │
│ → NOT locked (can be resubmitted)                              │
│ → Rejection reason captured in AuditLog                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│               STEP 5: REPORTING & COMPLIANCE                    │
├─────────────────────────────────────────────────────────────────┤
│ Approved records used in carbon emission reports               │
│ AuditLog proves:                                                │
│ • Data wasn't modified after approval                          │
│ • Who approved and when                                        │
│ • What changed and why                                         │
│ • Complete chain of custody                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Modules

### 1. ActivityRecord (Core Data Model)
```python
# Represents single emissions event/consumption period
tenant_id          # Multi-tenancy
raw_row_id         # Link to immutable source data
source_type        # "sap", "utility", "travel"
activity_type      # "fuel", "electricity", "flight", "hotel", etc.
scope              # "scope_1", "scope_2", "scope_3" (GHG Protocol)
status             # "valid", "suspicious", "invalid", "approved", "rejected"
is_locked          # True = cannot edit (compliance protection)
quantity_original  # As received from source
quantity_normalized# Standardized for calculations
approved_by        # User who approved
approved_at        # When approved
created_at         # When imported
```

**Key Methods:**
- `can_be_approved()` - Check if record eligible for approval
- `build_activity_snapshot()` - Capture state for audit trail

### 2. ValidationIssue (Data Quality Tracking)
```python
# Problem found during import validation
activity_record_id
severity           # "error" (critical), "warning" (informational)
code              # Machine-readable: "MISSING_FACILITY_ID", "OUTLIER_QUANTITY"
message           # Human-readable explanation
created_at        # When detected
```

### 3. RawActivityRow (Immutable Source Data)
```python
# Exact copy of data as received - NEVER modify
import_batch_id
row_number        # Position in original file
raw_payload       # Complete JSON as received
raw_hash          # SHA256 for deduplication
```

**Design Principle:** Immutability proves data integrity in compliance audits.

### 4. ImportBatch (Upload Session)
```python
# Tracks single file upload and processing
tenant_id
source_system_id  # Which external system provided data
original_filename # User's uploaded file name
status            # "processing", "completed", "failed"
total_rows        # Stats: total in file
valid_rows        # Stats: passed validation
invalid_rows      # Stats: has errors
suspicious_rows   # Stats: needs review
```

### 5. AuditLog (Compliance Trail)
```python
# Record of every significant action
tenant_id
actor             # User who performed action
action            # "approved", "rejected", "deleted"
entity_type       # "ActivityRecord", "ImportBatch"
entity_id         # Which record changed
before            # JSON snapshot before change
after             # JSON snapshot after change
message           # Human-readable description
created_at        # When action occurred
```

### 6. Tenant (Organization)
```python
# Customer in multi-tenant SaaS
name              # Organization name (unique)
created_at        # Account creation date
```

---

## API Endpoints

### ActivityRecord Endpoints
All under `/api/activity-records/`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | List records (supports filters) |
| GET | `/{id}/` | Get single record |
| PATCH | `/{id}/` | Update record (if not locked) |
| GET | `/summary/` | Get statistics (total, valid, approved, etc.) |
| POST | `/{id}/approve/` | Approve & lock record |
| POST | `/{id}/reject/` | Reject record |

### Filters (Query Parameters)
```
GET /api/activity-records/?tenant_id=1&status=valid&source_type=sap
  tenant_id=1         → Only records from org 1
  status=valid        → Only valid records
  source_type=sap     → Only from SAP source
```

### Approve Action
```
POST /api/activity-records/123/approve/
Response: {"id": 123, "status": "approved", "is_locked": true, ...}

Preconditions:
- Record must be "valid" or "suspicious"
- Record must NOT be locked
Creates:
- Sets approved_by, approved_at
- Locks record (is_locked=true)
- Creates AuditLog entry
```

### Reject Action
```
POST /api/activity-records/123/reject/
Body: {"reason": "Facility code mismatch"}
Response: {"id": 123, "status": "rejected", "is_locked": false, ...}

Preconditions:
- Record must NOT be locked (cannot reject approved records)
Behavior:
- Sets status to "rejected"
- Does NOT lock (allows resubmission)
```

---

## Database Models

### Entity Relationship Diagram

```
Tenant (Organization)
  ├─ ActivityRecord (Emissions data)
  │   ├─ ValidationIssue (Data quality issues)
  │   └─ [linked to] RawActivityRow
  │
  ├─ RawActivityRow (Immutable source)
  │   └─ [linked from] ImportBatch
  │
  ├─ ImportBatch (Import session)
  │   ├─ SourceSystem
  │   └─ RawActivityRow (many)
  │
  └─ AuditLog (Change tracking)
```

### Multi-Tenancy Enforcement

Every model has `ForeignKey(Tenant, on_delete=models.CASCADE)`:
```python
# When querying, always filter by tenant:
ActivityRecord.objects.filter(tenant_id=user_org_id)

# Prevents cross-organization data leaks
# Deleting Tenant cascades to all related data
```

---

## Key Design Patterns

### 1. Immutability for Compliance
- RawActivityRow never modified
- ActivityRecord locked after approval
- Enables audit trails proving data integrity

### 2. Atomic Transactions
```python
with transaction.atomic():
    record.status = "approved"
    record.save()
    AuditLog.objects.create(...)  # If fails, record change rolled back
```
Prevents orphaned audit records.

### 3. Snapshots for Audit Trails
```python
before_snapshot = build_activity_snapshot(record)
# Make changes
after_snapshot = build_activity_snapshot(record)
AuditLog.objects.create(before=before_snapshot, after=after_snapshot)
```
Proves what changed and why.

### 4. Query Optimization
```python
# Avoid N+1 queries:
queryset.select_related("tenant", "raw_row")      # Join tables
queryset.prefetch_related("issues")                # Load relations efficiently
```

### 5. Read-Only Fields in Serializer
```python
read_only_fields = ["status", "is_locked", "approved_by", "approved_at"]
# Client cannot set these directly - only via approve/reject actions
```

---

## Interview Talking Points

### 1. Multi-Tenancy Architecture
**"We use Tenant model as root for complete data isolation. Every model has ForeignKey to Tenant, so one customer can never see another's data. On_delete=CASCADE ensures if organization deleted, all their data cleaned up."**

### 2. Approval Workflow & Compliance
**"ActivityRecord has lifecycle: valid → suspicious → invalid, then analyst approves or rejects. Approved records get locked (is_locked=true) so they can't be modified - proof of compliance. Before/after snapshots create AuditLog proving data integrity."**

### 3. Data Immutability
**"RawActivityRow stores exact copy of data as received. Never modified. This proves in compliance audits that we didn't tamper with source data. If import has issues, we reject batch and reimport - raw data immutable."**

### 4. Atomic Transactions
**"When approving, we update record AND create AuditLog in single transaction. If AuditLog creation fails, entire approval rolls back. Prevents orphaned audit records."**

### 5. Validation System
**"Import creates ValidationIssue for each problem: errors (critical) and warnings (informational). Record can still be "valid" with warnings, but analyst reviews before approving."**

### 6. GHG Protocol Integration
**"We classify emissions by Scope (1/2/3) per international standard:
- Scope 1: Direct (company vehicles, on-site fuel)
- Scope 2: Indirect energy (purchased electricity)
- Scope 3: Other indirect (travel, supply chain)
This determines how emissions are reported in compliance documents."**

### 7. Query Performance
**"Use select_related() for JOINs (avoids N+1), prefetch_related() for reverse relations. For large imports, we could batch operations or use Celery for async processing."**

### 8. API Design (REST)
**"GET /activity-records/ lists records (filterable by tenant, status, source). POST /activity-records/{id}/approve/ is custom action for workflow. PATCH lets analysts correct data. Serializers validate input and denormalize responses (e.g., include tenant_name so client doesn't need extra request)."**

---

## Study Plan for Interview

### Quick Reference
1. **5-minute overview:** Multi-tenant SaaS, imports → validates → approves → reports
2. **Key files to know:**
   - `config/settings.py` - installed apps, middleware, CORS
   - `config/urls.py` - main routing
   - `activities/models.py` - ActivityRecord, ValidationIssue
   - `activities/views.py` - REST endpoints, approve/reject
   - `ingestion/models.py` - ImportBatch, RawActivityRow
   - `audit/models.py` - AuditLog

### Deep Dive Topics
1. **Multi-tenancy:** How data is isolated per customer
2. **Approval workflow:** Status transitions, locking, audit trails
3. **Data validation:** ValidationIssue severity levels, error codes
4. **Compliance:** How immutability and audit logs prove integrity

### Demo Points
1. List records with filters: `GET /api/activity-records/?tenant_id=1&status=valid`
2. Approve record: `POST /api/activity-records/123/approve/`
3. Admin interface: View ActivityRecord, ValidationIssue, AuditLog, ImportBatch
4. Database: Show how Tenant isolation works

---

## Running the Backend

```bash
# Navigate to backend directory
cd backend

# Activate virtual environment
source .venv/bin/activate  # Mac/Linux
# or
.venv\Scripts\Activate     # Windows

# Run development server
python manage.py runserver

# Run admin interface
# Visit: http://localhost:8000/admin/

# Create superuser
python manage.py createsuperuser

# Run migrations (apply database schema)
python manage.py migrate

# Run tests
python manage.py test
```

---

## Common Interview Questions

**Q: How do you prevent data leaks in multi-tenant system?**
A: Every model has ForeignKey to Tenant. When querying, we filter by tenant_id. Serializer requires client to provide tenant_id. Database constraints prevent cross-org queries.

**Q: What happens if approval fails?**
A: We use transaction.atomic(). If AuditLog creation fails, the entire transaction rolls back - record status reverts, no partial changes.

**Q: How do you handle large file imports?**
A: Currently synchronous. For scale: use Celery for async processing, batch database inserts, implement file streaming for large CSVs, use database transactions with savepoints.

**Q: Why lock records after approval?**
A: Compliance requirement. Locked records prevent modification, proving data integrity in carbon audits. If error found, reject and reimport.

**Q: How is data quality measured?**
A: ImportBatch tracks stats: total_rows, valid_rows, invalid_rows, suspicious_rows. Get summary: GET /activity-records/summary/ shows count by status.

---

**End of Backend Guide**

*Last updated: May 2026*
*For interview preparation - covers architecture, design patterns, and key files*
