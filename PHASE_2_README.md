# Phase 2 — Backend Foundation & Data Contracts

## Goal

Build the backend foundation for the AI-Based Fake Identity & Document Screening System.

Phase 2 does **not** implement real AI detection models yet. It creates the stable backend contract that every later AI/security stage will use.

---

## Phase 2 Scope

We will build:

1. FastAPI application
2. Environment/configuration management
3. Shared Pydantic schemas
4. Initial database layer
5. Case creation and retrieval
6. File upload handling
7. Authentication/RBAC scaffolding
8. API versioning
9. Health/status endpoints
10. Structured error handling
11. Logging foundation
12. Pipeline input/output contracts
13. Basic Docker development setup

---

## Architecture

```text
Client / Officer Dashboard
          |
          v
     FastAPI API
          |
    ┌─────┴─────┐
    |           |
  Auth       Case API
    |           |
    └─────┬─────┘
          v
    Case Service
          |
    ┌─────┴──────────────┐
    |                    |
    v                    v
 Database            File Storage
    |
    v
Pipeline Contracts
    |
    v
Future AI Pipeline
```

---

## Phase 2 Principle

The backend must be independent of any particular AI model.

Later we should be able to replace:

```text
PaddleOCR
Tesseract
InsightFace
Liveness model
Tampering model
Ollama model
```

without rewriting the API contract.

---

# 1. Project Structure

Target structure:

```text
identity-screening-system/
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── requirements.txt
│   │
│   ├── api/
│   │   ├── routes.py
│   │   └── dependencies.py
│   │
│   ├── models/
│   │   └── schemas.py
│   │
│   ├── services/
│   │   ├── case_service.py
│   │   └── file_service.py
│   │
│   ├── pipeline/
│   │   └── contracts.py
│   │
│   ├── security/
│   │   └── auth.py
│   │
│   ├── db/
│   │   └── database.py
│   │
│   └── utils/
│       └── logging.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── synthetic/
│
├── frontend/
│   └── index.html
│
├── tests/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

# 2. API Versioning

All application endpoints use:

```text
/api/v1/
```

Examples:

```text
GET  /api/v1/health
POST /api/v1/auth/dev-token
POST /api/v1/cases
GET  /api/v1/cases/{case_id}
POST /api/v1/cases/{case_id}/documents
POST /api/v1/cases/{case_id}/screen
```

`dev-token` is development-only and must never be considered production authentication.

---

# 3. Health API

### Endpoint

```http
GET /api/v1/health
```

### Response

```json
{
  "status": "ok",
  "service": "identity-screening-api",
  "version": "0.1.0"
}
```

This endpoint is used for:

- local testing
- Docker health checks
- future Kubernetes probes

---

# 4. Case Model

A case represents one identity-screening request.

### Required fields

```json
{
  "case_id": "CASE-000001",
  "status": "created",
  "created_at": "2026-09-16T00:00:00Z",
  "created_by": "officer_001"
}
```

### Initial statuses

```text
created
uploaded
processing
completed
flagged
reviewed
closed
failed
```

---

# 5. Document Input

A screening case can contain multiple input files.

Initial supported categories:

```text
document_image
live_capture
face_frame
```

Example:

```json
{
  "case_id": "CASE-000001",
  "files": [
    {
      "file_id": "FILE-001",
      "type": "document_image",
      "filename": "document.jpg",
      "sha256": "..."
    },
    {
      "file_id": "FILE-002",
      "type": "live_capture",
      "filename": "capture.jpg",
      "sha256": "..."
    }
  ]
}
```

The system stores a SHA-256 hash for every uploaded file.

---

# 6. Input Validation

Before any AI processing:

```text
Upload
  |
  v
Extension check
  |
  v
MIME/type check
  |
  v
Size limit
  |
  v
Hash generation
  |
  v
File registration
```

Initial accepted image formats:

```text
JPG
JPEG
PNG
WEBP
```

Do not trust the filename extension alone. MIME/content validation must be added to the file service.

---

# 7. Pipeline Contract

Every pipeline stage should eventually return a common structure.

```json
{
  "stage": "ocr",
  "status": "completed",
  "confidence": 0.94,
  "duration_ms": 412,
  "result": {},
  "warnings": [],
  "model": "paddleocr",
  "version": "pending"
}
```

Possible status values:

```text
pending
processing
completed
failed
skipped
```

This contract makes every stage swappable.

---

# 8. Planned Stage Contracts

## Preprocessing

Input:

```json
{
  "file_id": "FILE-001",
  "path": "...",
  "mime_type": "image/jpeg"
}
```

Output:

```json
{
  "stage": "preprocessing",
  "status": "completed",
  "image_quality": 0.91,
  "document_detected": true,
  "rotation": 2.4,
  "output_path": "..."
}
```

---

## OCR

Input:

```text
preprocessed document
```

Output:

```json
{
  "stage": "ocr",
  "status": "completed",
  "confidence": 0.95,
  "fields": {
    "name": "...",
    "document_number": "...",
    "date_of_birth": "...",
    "expiry_date": "..."
  }
}
```

---

## Tampering Detection

Output:

```json
{
  "stage": "tampering",
  "status": "completed",
  "tampering_score": 0.17,
  "is_suspected": false,
  "signals": []
}
```

---

## Liveness / Deepfake

Output:

```json
{
  "stage": "liveness",
  "status": "completed",
  "liveness_score": 0.96,
  "spoof_score": 0.04,
  "deepfake_score": 0.02
}
```

---

## Validation

Output:

```json
{
  "stage": "validation",
  "status": "completed",
  "valid": true,
  "field_mismatches": [],
  "warnings": []
}
```

---

## Face Verification

Output:

```json
{
  "stage": "face_verification",
  "status": "completed",
  "similarity": 0.89,
  "match": true
}
```

The final threshold will be calibrated later with proper evaluation data. Do not treat `0.89` as a production threshold.

---

## Anomaly Detection

Output:

```json
{
  "stage": "anomaly",
  "status": "completed",
  "anomaly_score": 0.63,
  "signals": [
    {
      "type": "device_reuse",
      "severity": "medium"
    }
  ]
}
```

---

## Risk Scoring

Output:

```json
{
  "stage": "risk_scoring",
  "status": "completed",
  "risk_score": 38,
  "risk_level": "medium",
  "signals": []
}
```

Risk scoring remains a deterministic backend component, not an LLM decision.

---

# 9. Database — Phase 2

Start with SQLite for local development.

Future production database:

```text
PostgreSQL
```

Initial entities:

```text
users
cases
files
pipeline_runs
pipeline_results
audit_events
```

Later entities:

```text
identities
devices
face_embeddings
watchlist_entries
fraud_signals
officer_decisions
```

---

# 10. User Roles

Initial roles:

```text
officer
admin
auditor
```

Permissions:

| Action | Officer | Admin | Auditor |
|---|---:|---:|---:|
| Create case | Yes | Yes | No |
| Upload evidence | Yes | Yes | No |
| Run screening | Yes | Yes | No |
| View case results | Yes | Yes | Yes |
| Verify audit chain | No | Yes | Yes |
| Manage users | No | Yes | No |
| Modify audit records | No | No | No |

These are application permissions for the prototype; real government authorization policy would need separate approval.

---

# 11. Authentication

Phase 2 will include a development authentication mechanism.

Development:

```text
POST /api/v1/auth/dev-token
```

Production target:

```text
OAuth2 / OIDC
       |
       v
Government Identity Provider
       |
       v
JWT
       |
       v
RBAC
```

The development token endpoint must be disabled in production.

---

# 12. Environment Variables

Create:

```text
.env
```

from:

```text
.env.example
```

Example:

```env
APP_ENV=development
APP_NAME=identity-screening-api
API_V1_PREFIX=/api/v1

DATABASE_URL=sqlite:///./screening.db

JWT_SECRET=CHANGE_ME
ENCRYPTION_KEY=CHANGE_ME

MAX_UPLOAD_MB=10

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:4b
```

Never commit real secrets.

---

# 13. File Storage

Phase 2 local storage:

```text
data/uploads/
```

Later production storage:

```text
S3-compatible object storage
```

Files should be referenced by generated IDs rather than trusting user-supplied filenames.

Example:

```text
FILE-001
FILE-002
```

---

# 14. Hashing

Every uploaded file receives:

```text
SHA-256(file_bytes)
```

Purpose:

```text
input integrity
audit linkage
duplicate detection
tamper-evidence
```

Example:

```json
{
  "file_id": "FILE-001",
  "sha256": "..."
}
```

Do not store sensitive raw data on the blockchain.

---

# 15. Logging

Create structured application logs.

Example:

```json
{
  "timestamp": "...",
  "request_id": "...",
  "user_id": "officer_001",
  "action": "case.create",
  "case_id": "CASE-000001",
  "status": "success"
}
```

Never log raw:

```text
ID numbers
full PII
face images
authentication secrets
encryption keys
```

---

# 16. Error Contract

All API errors should follow one format:

```json
{
  "error": {
    "code": "INVALID_FILE",
    "message": "Unsupported or invalid image file.",
    "request_id": "REQ-001"
  }
}
```

This makes frontend handling predictable.

---

# 17. Phase 2 API List

### System

```text
GET /api/v1/health
```

### Authentication

```text
POST /api/v1/auth/dev-token
```

### Cases

```text
POST /api/v1/cases
GET  /api/v1/cases
GET  /api/v1/cases/{case_id}
```

### Files

```text
POST /api/v1/cases/{case_id}/files
GET  /api/v1/cases/{case_id}/files
```

### Screening

For Phase 2 this endpoint only validates the request and returns a placeholder pipeline state:

```text
POST /api/v1/cases/{case_id}/screen
```

Real pipeline execution comes in Phase 3.

---

# 18. Phase 2 Definition of Done

Phase 2 is complete when:

```text
[ ] FastAPI starts successfully
[ ] /docs works
[ ] Health endpoint works
[ ] Dev authentication works
[ ] RBAC middleware works
[ ] Case can be created
[ ] Case can be retrieved
[ ] Image can be uploaded
[ ] SHA-256 hash is generated
[ ] Files are stored safely
[ ] Database records are created
[ ] Pipeline schemas exist
[ ] Error responses are standardized
[ ] Structured logging works
[ ] Docker startup works
[ ] Basic tests pass
```

---

# 19. What We Do NOT Build in Phase 2

Do not add real:

```text
OCR model
Tampering model
Liveness model
Deepfake model
Face recognition
Anomaly ML
Blockchain network
Kubernetes
Kafka
Redis
FAISS
```

Those belong to later phases.

---

# 20. Phase 2 → Phase 3 Transition

At the end of Phase 2:

```text
Frontend
   |
   v
FastAPI
   |
   v
Case + File
   |
   v
Pipeline Contract
```

Phase 3 will connect:

```text
Preprocessing
      ↓
┌─────┼───────────┐
↓     ↓           ↓
OCR  Tampering  Liveness
└─────┼───────────┘
      ↓
Validation
      ↓
Face Verification
      ↓
Anomaly
      ↓
Risk
```

All stages will initially use controlled mocks so the complete pipeline can be tested before real models are introduced.

---

# Phase 2 Deliverables

```text
backend/
├── main.py
├── config.py
├── api/
├── models/
├── services/
├── security/
├── db/
└── pipeline/

.env.example
docker-compose.yml
tests/
```

## Success criterion

A fresh clone should be able to start the API and perform:

```text
Create user/session
       ↓
Create case
       ↓
Upload document image
       ↓
Calculate SHA-256
       ↓
Store metadata
       ↓
Return valid case/file IDs
```

without requiring any AI model.

---

## Next Phase

**Phase 3 — Complete Mock Verification Pipeline**

Goal:

```text
Case
 ↓
Preprocessing
 ↓
OCR + Tampering + Liveness (parallel)
 ↓
Validation
 ↓
Face Verification
 ↓
Anomaly Detection
 ↓
Risk Scoring
 ↓
Complete structured result
```

Only after that will we begin replacing individual mocks with real models.
