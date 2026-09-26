# AI-Based Fake Identity & Document Screening System

**SIH Problem Statement:** SIH26188
**Theme:** Blockchain & Cybersecurity
**Organization:** Ministry of Home Affairs

> A privacy‑aware, explainable identity and document screening platform that combines document forensics, OCR, biometric verification, liveness/deepfake detection, cross‑case fraud analytics, cybersecurity controls, and tamper‑evident audit logging.

---

## 1. Project Vision

The system assists authorized officers in reviewing identity‑verification cases by aggregating multiple independent signals rather than relying on a single document or face‑match score. The high‑level workflow is:

```
Document + Live Capture + Face Frames
    |
    v
Secure API Gateway
    |
    v
Pipeline Orchestrator
    |
    +-----------------------------+
    |   Verification Pipeline   |
    +-----------------------------+
    |
    +-------+-------+-------+
    |       |       |       |
   OCR  Tampering  Liveness
    |       |       |
    +-------+-------+
    |
    v
Validation & Watchlist
    |
    v
Face Verification
    |
    v
Anomaly Detection
    |
    v
Risk Scoring
    |
    +-------+-------+
    |               |
    v               v
Audit Hash Chain   Case Database
    |
    v
Audit / Ledger Layer
    |
    v
Officer Dashboard
```

The demo uses deterministic/mock adapters for AI‑heavy components; each adapter has a well‑defined extension point for later replacement.

---

## 2. Core Objectives

1. Detect suspicious or manipulated identity documents.
2. Extract and normalize document fields.
3. Verify that the presenter is a live person.
4. Compare the live face with the document face.
5. Detect suspicious patterns across multiple cases.
6. Produce an **explainable** risk score (not a legal decision).
7. Protect sensitive information via authentication, RBAC, encryption, and controlled access.
8. Maintain a tamper‑evident audit trail (hash‑chain, future permissioned blockchain).
9. Provide an officer‑facing dashboard with evidence, signals, explanations and audit history.

**Non‑objectives for the first demo** – no real citizen PII, no national‑scale government databases, no production claims, and no reliance on unavailable government APIs.

---

## 3. Design Principles

* **Multi‑signal verification** – no single signal is decisive.
* **Explainability first** – officers see why a score was produced.
* **Privacy by design** – raw documents/biometrics remain in controlled storage; the audit layer stores only hashes and metadata.
* **Swappable services** – each stage exposes a stable interface for mock → production replacement.
* **Deterministic risk scoring** – fully reproducible and auditable.

---

## 4. High‑Level Architecture

### 4.1 Client layer
* Officer web dashboard (future mobile capture client)
* Document & camera upload UI

### 4.2 API Gateway (FastAPI)
* Authentication (JWT‑scaffold → OAuth2/OIDC)
* RBAC enforcement
* Request validation, rate‑limiting, TLS termination, correlation IDs, security logging

### 4.3 Pipeline Orchestrator
* Owns case lifecycle, invokes verification services in order (parallel where possible)

### 4.4 Verification Services (conceptual stages)
1. Preprocessing & Classification
2. OCR Extraction
3. Tampering Detection
4. Liveness & Deepfake Detection
5. Validation & Watchlist Rules
6. Face Verification
7. Cross‑Case Anomaly Detection
8. Explainable Risk Scoring
9. Audit Anchoring (hash‑chain)

### 4.5 Data Layer (initial demo)
* PostgreSQL (or SQLite) for case metadata & results
* Redis for velocity / rate windows (future)
* FAISS/pgvector for similarity search (future)
* Encrypted object storage for uploaded artifacts

### 4.6 Audit Layer (initial)
* Append‑only hash chain: `hash(prev_hash + payload)` → `current_hash`
* Future: anchor hashes to a permissioned blockchain (e.g., Hyperledger Fabric)

---

## 5. Detailed Verification Workflow (Stage contracts are defined in `docs/PIPELINE_CONTRACTS.md`)

*Stage 0 – Case creation* → inputs: document images, live capture frames, optional video, submission metadata → outputs: `case_id`, file hashes, capture metadata, correlation ID.

*Stage 1 – Preprocessing & classification* – image quality, blur, rotation, perspective correction, document type classification.

*Stage 2A – OCR extraction* – text extraction, field detection, confidence per field, optional MRZ parsing.

*Stage 2B – Document tampering detection* – heuristics (ELA, compression artifacts, font/layout anomalies) + research data (DocTamper).

*Stage 2C – Liveness & deepfake detection* – face detection → anti‑spoof model → texture/motion signals → optional active challenge.

*Stage 3 – Validation & watchlist* – field presence, format checks, expiry, synthetic watchlist matching.

*Stage 4 – Face verification* – document‑face vs live‑face similarity using InsightFace/ArcFace embeddings.

*Stage 5 – Cross‑case anomaly detection* – reuse of face embeddings, device fingerprint reuse, velocity anomalies, relational patterns.

*Stage 6 – Explainable risk scoring* – weighted sum of normalized stage signals.

*Stage 7 – Audit anchoring* – deterministic event serialization, hash‑chain, future blockchain anchor.

*Stage 8 – Officer dashboard* – case overview, evidence panels, explainability panel, audit panel, officer actions.

---

## 6. API Plan (primary contract in `docs/API_CONTRACTS.md`)

Base URL: `http://localhost:8000/api/v1`

* **GET** `/health` – health check.
* **POST** `/auth/dev-token` – development token issuance (replace with OAuth2/OIDC in production).
* **POST** `/cases` – create a new case (returns `case_id`).
* **GET** `/cases` – list cases.
* **GET** `/cases/{case_id}` – retrieve case details.
* **POST** `/cases/{case_id}/files` – upload document / live‑capture files.
* **GET** `/cases/{case_id}/files` – list uploaded files.
* **POST** `/cases/{case_id}/screen` – trigger screening pipeline (mock deterministic response in Phase 1).
* **GET** `/cases/{case_id}/screen` – retrieve screening results.
* **GET** `/cases/{case_id}/audit` – fetch audit chain events for the case.

---

## 7. Security Architecture (full detail in `docs/SECURITY_ARCHITECTURE.md`)

* Authentication – JWT development scaffold → OAuth2/OIDC production.
* RBAC – roles: OFFICER, ADMIN, AUDITOR with granular permissions.
* TLS in production, rate limiting, file‑size limits, MIME validation, antivirus scanning hook.
* Field‑level encryption for PII, secret management via environment variables, no hard‑coded secrets.
* Audit logging for all privileged actions, separation of raw biometric data from logs.
* Threat model & abuse‑case considerations are documented separately.

---

## 8. Data Strategy (see `docs/DATA_STRATEGY.md`)

### Core datasets (research only)
* **MIDV‑500** – document detection & OCR benchmarking.
* **MIDV‑2019** – harder document‑image conditions.
* **PaddleOCR / Tesseract** – OCR engines.
* **OpenCV** – preprocessing, quality analysis.
* **DocTamper** – document‑tampering research.
* **CelebA‑Spoof** – anti‑spoofing research.
* **FaceForensics++** – deep‑fake research.
* **OULU‑NPU** – optional anti‑spoofing evaluation.
* **InsightFace / ArcFace** – face detection & embeddings.
* **FAISS / pgvector** – vector similarity for face reuse detection.
* **Redis** – velocity / rate support.
* **Hyperledger Fabric** – future permissioned blockchain audit integration.

**Synthetic data** – mock watchlists, MRZ samples, fraud/anomaly cases, tampered documents, consented face data, audit‑chain events.

All real‑world PII is excluded; synthetic or properly authorized data only.

---

## 9. Database Design (see `docs/DATABASE_DESIGN.md`)

Entities: users, roles, cases, case_files, screening_runs, stage_results, extracted_identity_fields, face_references, anomaly_events, risk_results, audit_events, watchlist_records, device_signals.

Relationships enforce minimal storage of raw biometric data; sensitive fields are encrypted and separated from analytical metadata.

---

## 10. Audit / Blockchain Design (see `docs/AUDIT_BLOCKCHAIN.md`)

Append‑only audit events contain:
* `event_id`
* `timestamp`
* `actor`
* `event_type`
* `case_id`
* `screening_run_id`
* `previous_hash`
* `current_hash`
* `metadata`

Hash‑chain creation, integrity verification, tamper detection, and future Hyperledger Fabric anchoring are described.

---

## 11. Testing Strategy (see `docs/TESTING_STRATEGY.md`)

* Unit, integration, API, pipeline, security, OCR evaluation, tampering detection, liveness, face verification, deep‑fake, anomaly detection, deterministic risk‑engine, audit integrity, performance, end‑to‑end, adversarial testing.

---

## 12. Development Roadmap (see `docs/DEVELOPMENT_ROADMAP.md`)

**Phase 1** – Architecture, specification & data strategy (current).
**Phase 2** – Backend skeleton, FastAPI, DB, authentication, contracts.
**Phase 3** – Full mock screening pipeline (deterministic outputs).
**Phase 4** – Real preprocessing + OCR integration.
**Phase 5** – Real AI, security hardening, blockchain integration, production readiness.

Only documentation is created in Phase 1 – no code implementation, no model downloads.

---

## 13. Development Conventions

* Python 3.11+, type hints, modular services.
* No hard‑coded secrets or absolute Windows paths.
* Environment‑based configuration (`.env.example`).
* Clear naming, minimal dependencies, no giant files.
* All AI modules are replaceable through well‑defined contracts.

---

## 14. Demo Workflow (for SIH presentation)

1. Officer logs in.
2. Creates a case.
3. Uploads document + live capture.
4. Screening pipeline runs (mock deterministic results).
5. Risk score and explainable reasons are shown.
6. Officer reviews evidence and audit chain.
7. Audit integrity check demonstrates tamper detection.

---

*This document is the single source of truth for the system architecture. All other Phase 1 documentation files reference the definitions here.*
