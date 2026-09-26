# Database Design

The data model is intentionally minimal, focusing on **case lifecycle**, **stage results**, and **auditability** while avoiding storage of raw biometric or document images. All large binary artifacts are stored externally (object storage) and referenced by hash.

---

## Core Entities

| Table / Collection | Primary Key | Description |
|---|---|---|
| **users** | `user_id` (UUID) | System users (officers, admins, auditors). Stores username, hashed password, role reference. |
| **roles** | `role_name` (string) | RBAC roles (`OFFICER`, `ADMIN`, `AUDITOR`). |
| **cases** | `case_id` (UUID) | Top‑level case record. Links to the submitting officer, creation timestamp, status, and metadata. |
| **case_files** | `file_id` (UUID) | Uploaded artefacts (document images, live capture videos). Stores `case_id` FK, `file_type` (`document`/`live_capture`), content hash, storage URI, upload timestamp. |
| **screening_runs** | `run_id` (UUID) | Each invocation of the verification pipeline. Links to `case_id`, start/end timestamps, overall status. |
| **stage_results** | Composite PK (`run_id`, `stage_name`) | Stores JSON payload for each pipeline stage (see `docs/PIPELINE_CONTRACTS.md`). Includes `status`, `output`, `confidence`, `metadata`. |
| **extracted_identity_fields** | `field_id` (UUID) | Normalized fields extracted from OCR (name, dob, document number, etc.) with per‑field confidence. Linked to `run_id`. |
| **face_references** | `ref_id` (UUID) | Stores face embeddings for both document and live capture. Contains hash of raw image, encrypted embedding, and linkage to `run_id`. |
| **anomaly_events** | `event_id` (UUID) | Results of cross‑case anomaly detection (e.g., face reuse, velocity spikes). |
| **risk_results** | `result_id` (UUID) | Final deterministic risk score and band, with reasoning list. Linked to `run_id`. |
| **audit_events** | `event_id` (UUID) | Immutable audit chain entries (see `docs/AUDIT_BLOCKCHAIN.md`). |
| **watchlist_records** | `watch_id` (UUID) | Synthetic watchlist entries used for validation (e.g., fake watchlist names, IDs). |
| **device_signals** | `signal_id` (UUID) | Optional device fingerprint data (IP, user‑agent, device ID) associated with a case. |

---

## Relationships

- `users` (1) — (*) `cases` (an officer may create many cases).
- `cases` (1) — (*) `case_files` (multiple uploads per case).
- `cases` (1) — (*) `screening_runs` (re‑screening possible).
- `screening_runs` (1) — (*) `stage_results` (one row per stage).
- `screening_runs` (1) — (*) `extracted_identity_fields`.
- `screening_runs` (1) — (*) `face_references`.
- `screening_runs` (1) — (*) `anomaly_events`.
- `screening_runs` (1) — 1 `risk_results`.
- `screening_runs` (1) — (*) `audit_events` (each stage appends an event).

---

## Sensitive Data Handling

- **PII fields** (e.g., `name`, `dob`, `document_number`) are stored encrypted using a per‑field symmetric encryption key (`ENCRYPTION_KEY` from the environment). The encryption key is never committed.
- **Biometric embeddings** are encrypted similarly; raw images are not stored in the database, only a hash and a secure storage URI.
- **Audit events** never contain raw PII; they store only hashes and limited metadata.

---

## Example Schema Snippets (SQL / SQLAlchemy‑style)

```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role_name TEXT REFERENCES roles(role_name)
);

CREATE TABLE cases (
    case_id UUID PRIMARY KEY,
    created_by UUID REFERENCES users(user_id),
    subject_name TEXT,
    status TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE case_files (
    file_id UUID PRIMARY KEY,
    case_id UUID REFERENCES cases(case_id),
    file_type TEXT CHECK (file_type IN ('document','live_capture')),
    storage_uri TEXT,
    content_hash TEXT,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE screening_runs (
    run_id UUID PRIMARY KEY,
    case_id UUID REFERENCES cases(case_id),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status TEXT
);

CREATE TABLE stage_results (
    run_id UUID REFERENCES screening_runs(run_id),
    stage_name TEXT,
    status TEXT,
    output JSONB,
    confidence FLOAT,
    metadata JSONB,
    PRIMARY KEY (run_id, stage_name)
);
```

---

*The concrete ORM models will be derived from this design in Phase 2. No tables are created at this time; this is purely a specification.*
