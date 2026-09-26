# API Contracts

Base URL for local development:
```
http://localhost:8000/api/v1
```

All request and response bodies are JSON. The API follows RESTful conventions and returns standard HTTP status codes (`200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `500 Internal Server Error`).

## 1. Health Check

- **GET** `/health`
- **Response**: `{ "status": "ok" }`
- No authentication required.

## 2. Authentication (Development Only)

- **POST** `/auth/dev-token`
- **Request**: `{ "user_id": "string" }`
- **Response**: `{ "access_token": "jwt-token", "token_type": "bearer" }`
- Returns a short‑lived JWT for the given user (development scaffold). In production this endpoint is replaced by OAuth2/OIDC.

## 3. Cases

### Create a Case
- **POST** `/cases`
- **Headers**: `Authorization: Bearer <token>`
- **Request**:
```json
{
  "subject_name": "string",
  "metadata": { "source": "string" }
}
```
- **Response** (`201 Created`): `{ "case_id": "uuid" }`

### List Cases
- **GET** `/cases`
- **Headers**: `Authorization: Bearer <token>`
- **Response** (`200 OK`):
```json
[ { "case_id": "uuid", "status": "string", "created_at": "iso8601" }, ... ]
```

### Retrieve a Case
- **GET** `/cases/{case_id}`
- **Headers**: `Authorization: Bearer <token>`
- **Response** (`200 OK`):
```json
{
  "case_id": "uuid",
  "subject_name": "string",
  "status": "string",
  "created_at": "iso8601",
  "files": [ { "file_id": "uuid", "type": "document|live-capture" } ]
}
```

## 4. File Management

### Upload Files
- **POST** `/cases/{case_id}/files`
- **Headers**: `Authorization: Bearer <token>`, `Content-Type: multipart/form-data`
- **Form fields**:
  - `file` – binary upload.
  - `type` – `document` or `live_capture`.
- **Response** (`201 Created`): `{ "file_id": "uuid", "filename": "string" }`

### List Files
- **GET** `/cases/{case_id}/files`
- **Headers**: `Authorization: Bearer <token>`
- **Response** (`200 OK`):
```json
[ { "file_id": "uuid", "filename": "string", "type": "document|live_capture" }, ... ]
```

## 5. Screening Pipeline

### Trigger Screening
- **POST** `/cases/{case_id}/screen`
- **Headers**: `Authorization: Bearer <token>`
- **Request**: (optional) `{ "force": false }`
- **Response** (`202 Accepted`): `{ "screening_run_id": "uuid", "status": "queued" }`
- In Phase 1 the pipeline returns deterministic mock results.

### Get Screening Results
- **GET** `/cases/{case_id}/screen`
- **Headers**: `Authorization: Bearer <token>`
- **Response** (`200 OK`):
```json
{
  "screening_run_id": "uuid",
  "status": "completed|failed",
  "results": {
    "ocr": { "status": "completed", "output": { ... } },
    "tampering": { "status": "completed", "output": { ... } },
    "liveness": { "status": "completed", "output": { ... } },
    "face_verification": { "status": "completed", "output": { ... } },
    "anomaly_detection": { "status": "completed", "output": { ... } },
    "risk_scoring": { "status": "completed", "output": { ... } }
  },
  "audit_chain": [ { "event_id": "...", "type": "...", "hash": "..." }, ... ]
}
```

## 6. Audit Retrieval

- **GET** `/cases/{case_id}/audit`
- **Headers**: `Authorization: Bearer <token>`
- **Response** (`200 OK`):
```json
[ { "event_id": "uuid", "timestamp": "iso8601", "actor": "user-id", "event_type": "stage_completed", "metadata": { ... }, "previous_hash": "...", "current_hash": "..." }, ... ]
```

---

*All endpoints respect RBAC: OFFICER can access own cases; ADMIN can access all; AUDITOR has read‑only access to audit data.*
