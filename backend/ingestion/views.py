"""
Views for data ingestion pipeline.

Currently empty - import processing is triggered via API/admin.

KEY CONCEPTS:
The ingestion pipeline processes CSV uploads in these steps:

1. UPLOAD PHASE
   - User uploads CSV file containing emissions data
   - File is stored and ImportBatch record created
   - Status: "processing"

2. PARSING PHASE
   - CSV is parsed row-by-row
   - Each row becomes a RawActivityRow (immutable)
   - Errors are tracked but don't stop processing

3. VALIDATION PHASE
   - Data validation rules run on each row
   - Missing required fields → error
   - Outliers or odd values → warning
   - ValidationIssue records created for each problem

4. RECORD CREATION PHASE
   - Validated data becomes ActivityRecord
   - Initial status: "valid", "suspicious", or "invalid"
   - Linked to raw data for traceability

5. ANALYST REVIEW PHASE
   - User reviews records in UI
   - Calls approve() or reject() on individual records
   - Approved records locked for compliance

FUTURE ENDPOINTS (if file upload API needed):
POST /api/ingestion/import/
    - Upload CSV file
    - Create ImportBatch
    - Trigger async processing (Celery task)
    - Return batch status URL

GET /api/ingestion/import/{batch_id}/
    - Check import status and progress
    - See validation statistics

GET /api/ingestion/import/{batch_id}/raw-rows/
    - View raw data received (for debugging)

See: ingestion/models.py (SourceSystem, ImportBatch, RawActivityRow)
See: ingestion/admin.py (admin interface for monitoring)
"""
