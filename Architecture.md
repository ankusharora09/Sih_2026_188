# AI-Based Fake Identity & Document Screening System

**SIH Problem Statement:** SIH26188  
**Theme:** Blockchain & Cybersecurity  
**Organization:** Ministry of Home Affairs  
**Project Type:** Software

> A privacy-aware, explainable identity and document screening platform that combines document forensics, OCR, biometric verification, liveness/deepfake detection, cross-case fraud analytics, cybersecurity controls, and tamper-evident audit logging.

---

## 1. Project Vision

The system is designed to help an authorized officer review an identity-verification case by combining multiple independent signals instead of trusting a single document or a single face-match score.

The target flow is:

```text
Document + Live Capture + Face Frames
                |
                v
        Secure API Gateway
                |
                v
         Pipeline Orchestrator
                |
                v
   +-----------------------------+
   |      Verification Pipeline  |
   +-----------------------------+
                |
        +-------+-------+
        |       |       |
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

The first implementation is a **working demo architecture**. AI-heavy components may initially use deterministic/mock adapters so the complete workflow is testable. Each adapter has an explicit extension point for replacing the demo logic with a production model.

---

# 2. Core Objectives

### Primary objectives

1. Detect suspicious or manipulated identity documents.
2. Extract and normalize document fields.
3. Verify that the person presenting the document is a live person.
4. Compare the live face with the document face.
5. Detect suspicious patterns across multiple cases.
6. Produce an explainable risk score rather than a black-box decision.
7. Protect sensitive information using authentication, RBAC, encryption and controlled access.
8. Maintain a tamper-evident audit history using a cryptographic hash chain, with a future path to a permissioned blockchain.
9. Provide an officer-facing dashboard showing evidence, signals, explanations and audit history.

### Non-objectives for the first demo

- Building a national-scale government identity database.
- Using real citizens' PII for development/testing.
- Claiming that mock AI outputs are production fraud detections.
- Depending on government-only APIs that the team cannot access during the hackathon.

---

# 3. Design Principles

### 3.1 Multi-signal verification

No single signal should be treated as absolute proof. The system combines OCR consistency, document integrity, liveness, face similarity, cross-case anomalies and rule-based validation.

### 3.2 Explainability first

The officer should see **why** a case received its risk score:

```text
Risk Score: 78 / 100

Contributing signals:
+28  Document tampering indicators
+20  Face mismatch
+15  Reused identity pattern
+10  Submission velocity anomaly
+05  OCR inconsistency
```

The exact weights will be finalized and tested during the risk-scoring phase.

### 3.3 Privacy by design

Sensitive raw documents and biometric material remain in controlled storage. The audit layer should primarily store hashes, event metadata and cryptographic proofs rather than unnecessary raw PII.

### 3.4 AI where AI adds value

LLMs are not used as the only fraud detector. Specialist computer-vision and OCR components handle visual/biometric tasks; the Ollama model is used where language reasoning, normalization and explanation are useful.

### 3.5 Swappable services

Every major stage exposes a stable interface so a mock can later be replaced without rewriting the whole system.

---

# 4. High-Level Architecture

## 4.1 Client layer

- Officer web dashboard
- Future mobile capture client
- Camera/document upload interface

## 4.2 API gateway

Responsibilities:

- Authentication
- Authorization / RBAC
- Request validation
- Rate limiting
- TLS termination in production
- Request/correlation IDs
- Security logging

## 4.3 Pipeline orchestrator

The orchestrator owns the case lifecycle and calls the verification services in the correct order.

The three expensive early checks are intended to run in parallel:

```python
ocr_result, tamper_result, liveness_result = await asyncio.gather(...)
```

This reduces unnecessary sequential latency.

## 4.4 Verification services

```text
1. Preprocessing & Classification
2. OCR Extraction
3. Tampering Detection
4. Liveness & Deepfake Detection
5. Validation & Watchlist Rules
6. Face Verification
7. Cross-Case Anomaly Detection
8. Explainable Risk Scoring
9. Audit Anchoring
```

## 4.5 Data layer

Initial demo:

- PostgreSQL or SQLite for case metadata and results
- Redis later for velocity/rate windows
- FAISS/pgvector later for similarity search
- Encrypted object/file storage for uploaded artifacts

## 4.6 Audit layer

Initial implementation:

```text
Event N
  hash(previous_hash + event_payload)
            |
            v
        current_hash
```

Future deployment:

```text
Application Audit Chain
          |
          v
Permissioned Blockchain
(e.g. Hyperledger Fabric)
```

The application should never put unnecessary raw PII directly on the blockchain.

---

# 5. Detailed Verification Workflow

## Stage 0 — Case creation

Inputs:

- Document image(s)
- Live capture / selfie frames
- Optional video sequence
- Submission metadata

Outputs:

- `case_id`
- file hashes
- capture metadata
- request/correlation ID

---

## Stage 1 — Preprocessing & classification

Tasks:

- Image quality check
- Blur detection
- Rotation correction
- Perspective correction
- Document boundary detection
- Crop and normalize
- Document type classification

Potential tools:

- OpenCV
- Pillow
- document segmentation model
- MIDV-500-based document localization/segmentation research

---

## Stage 2A — OCR extraction

Tasks:

- Extract text
- Detect expected fields
- Normalize names, dates and document numbers
- Confidence per field
- Optional MRZ parsing for supported documents

Primary candidates:

- PaddleOCR
- Tesseract

LLM assistance:

- normalize OCR output
- classify ambiguous field labels
- explain inconsistencies
- produce structured JSON from already-extracted text

The LLM is not the authoritative OCR engine.

---

## Stage 2B — Document tampering detection

Signals may include:

- text-region manipulation
- inconsistent compression/noise
- suspicious cloned regions
- inconsistent fonts/layout
- ELA-style forensic indicators
- model-based genuine/tampered classification

Research/data candidates:

- DocTamper
- synthetic tampering generated from clean document images

The exact production detector will be selected after a small benchmark.

---

## Stage 2C — Liveness & deepfake / presentation-attack detection

The goal is to distinguish a genuine live capture from attacks such as:

- photograph replay
- screen replay
- printed face presentation
- manipulated/AI-generated face presentation

Potential approach:

```text
Camera frames
      |
      +--> Face detection
      |
      +--> Passive anti-spoof model
      |
      +--> Texture / motion signals
      |
      +--> Optional active challenge
      |
      +--> Deepfake/manipulation signal
```

Research/data candidates:

- CelebA-Spoof
- OULU-NPU / similar presentation-attack datasets
- FaceForensics++ for manipulated-face research

Dataset licensing and permitted use must be checked before training or redistribution.

---

## Stage 3 — Validation & watchlist rules

Examples:

- Required fields present?
- Date format valid?
- Expiry date valid?
- Age/date consistency rules?
- Document number pattern valid?
- Cross-field consistency?
- MRZ/internal checksum where applicable?
- Demo watchlist match?

For the hackathon, watchlist data should be synthetic or explicitly authorized test data.

We will **not** depend on a public real-world blacklist as the core demo dependency.

---

## Stage 4 — Face verification

Goal:

```text
Document face  <----similarity---->  Live face
```

Potential stack:

- InsightFace / ArcFace embeddings
- cosine similarity
- face detection/alignment before embedding

Output example:

```json
{
  "match": true,
  "similarity": 0.87,
  "threshold": 0.60,
  "confidence": 0.94
}
```

Thresholds must be evaluated empirically rather than assumed.

---

## Stage 5 — Cross-case anomaly & fraud-pattern detection

Unlike document-level checks, this service looks across previous cases.

Signals:

- same face embedding/hash appearing under different identities
- repeated device fingerprint
- unusually high submission velocity
- repeated failed verification attempts
- suspicious IP/session relationships
- repeated document-number patterns

Initial demo can use relational queries and deterministic rules.

Upgrade path:

```text
Redis      -> velocity windows
FAISS      -> face similarity search
pgvector   -> vector search inside PostgreSQL
Graph DB   -> advanced relationship analysis later
```

---

## Stage 6 — Explainable risk scoring

The score is a weighted combination of independently produced signals.

Conceptual model:

```text
Risk Score =
    document_risk
  + tamper_risk
  + liveness_risk
  + face_risk
  + validation_risk
  + anomaly_risk
  + velocity_risk
```

All components are normalized to a known scale before aggregation.

Example output:

```json
{
  "risk_score": 74,
  "risk_band": "HIGH",
  "reasons": [
    "Document tampering signal detected",
    "Face similarity below configured threshold",
    "Identity reuse pattern observed"
  ]
}
```

The system should present this as a **decision-support signal**, not an automatic legal determination.

---

## Stage 7 — Blockchain-style audit anchoring

Every important case event is serialized deterministically and hashed.

Example:

```text
GENESIS
   |
   v
CASE_CREATED
   |
   v
OCR_COMPLETED
   |
   v
TAMPER_CHECK_COMPLETED
   |
   v
LIVENESS_COMPLETED
   |
   v
FACE_VERIFICATION_COMPLETED
   |
   v
RISK_SCORED
   |
   v
OFFICER_ACTION
```

Each record contains at least:

- event ID
- case ID
- timestamp
- actor ID
- event type
- payload hash
- previous hash
- current hash

Chain verification recomputes each hash and detects a broken link.

Future enhancement: anchor selected record hashes to a permissioned blockchain such as Hyperledger Fabric.

---

## Stage 8 — Officer dashboard

The dashboard should show:

### Case overview

- case ID
- document type
- submitted time
- current status
- overall risk score

### Evidence panels

- OCR extracted fields
- field confidence
- tampering indicators
- liveness result
- face similarity
- anomaly indicators
- validation/watchlist results

### Explainability panel

```text
WHY IS THIS CASE FLAGGED?

1. Face similarity below threshold
2. Suspected document text-region manipulation
3. Identity pattern reused in previous submissions
```

### Audit panel

- complete event timeline
- hash values
- chain status
- officer actions
- chain integrity verification button

### Officer actions

- Review
- Approve / reject according to authorized workflow
- Escalate
- Add note
- Request re-capture

---

# 6. Feature Set

## Citizen / Capture side (future-ready)

- Secure document upload
- Guided camera capture
- Live face capture
- Capture quality feedback
- Retry on poor image quality

## Officer side

- Login
- RBAC
- Case queue
- Case search
- Detailed verification report
- Risk explanations
- Evidence review
- Audit verification
- Escalation

## Admin side

- User/role management
- Threshold/configuration management
- Audit review
- Service health view

## Auditor side

- Read-only audit access
- Chain verification
- Case-event timeline
- Integrity report

---

# 7. API Plan

Base URL for local development:

```text
http://localhost:8000/api/v1
```

## Authentication

```http
POST /auth/dev-token        # DEVELOPMENT ONLY
```

Production replacement:

```text
OAuth2 / OIDC identity provider
```

## Cases

```http
POST /cases
GET  /cases/{case_id}
GET  /cases
```

## Screening

```http
POST /cases/{case_id}/screen
GET  /cases/{case_id}/screening
```

## Individual stage endpoints (useful for testing)

```http
POST /ocr
POST /tampering
POST /liveness
POST /face-verification
POST /anomaly
```

## Audit

```http
GET  /cases/{case_id}/audit
POST /audit/verify
```

## Admin / configuration

```http
GET /health
GET /config/public
```

The exact endpoint surface may be simplified after the first working backend pass.

---

# 8. Model Strategy — Ollama + Specialist Models

## Important architectural decision

**Ollama is the local LLM layer, not the entire computer-vision stack.**

The project needs specialist models/libraries for OCR, biometrics, anti-spoofing and image forensics.

## Ollama responsibilities

Use a local Ollama multimodal/reasoning model for:

- OCR result cleanup/normalization
- field-label interpretation
- rule explanation
- case summarization
- generating human-readable officer explanations
- structured JSON extraction from already-produced signals
- developer/agent assistance during implementation

## Current Ollama candidates

### `qwen3.5:4b`

Primary lightweight local candidate for the project laptop.

Why:

- multimodal text/image capability
- relatively small local footprint
- useful for UI/logic experiments and document-image reasoning

### `qwen3.5:9b`

Optional stronger local candidate if latency and RAM usage are acceptable.

### `qwen3-coder:30b`

Use for development/coding only if the machine/environment can support it. It is much larger than the project's local hardware target, so it is not the default runtime model.

### `glm-5.2:cloud` / other cloud tags

These are cloud-backed Ollama models and should not be treated as the project's guaranteed zero-cost local dependency. Local/offline development should remain possible with a local Qwen model.

Model availability and tags should be checked with:

```bash
ollama list
```

and the current Ollama model library before finalizing the deployment matrix.

---

# 9. Specialist AI / CV Stack

| Task | Initial implementation | Production/research direction |
|---|---|---|
| Image preprocessing | OpenCV + Pillow | Improved document-quality model |
| Document localization | OpenCV / segmentation model | MIDV-500-derived model |
| OCR | PaddleOCR or Tesseract | tuned document OCR + MRZ |
| Tampering | ELA + heuristics | DocTamper-trained detector / CNN |
| Face detection | InsightFace/OpenCV | production face detector |
| Face verification | ArcFace embeddings | calibrated biometric verification |
| Liveness | anti-spoof model | passive + optional active challenge |
| Deepfake | visual/frequency features | trained forensic classifier |
| Anomaly | rules + SQL | FAISS/pgvector + Redis |
| Risk scoring | Python weighted engine | calibrated/evaluated scoring model |
| Explanation | Ollama | constrained structured explanation layer |

---

# 10. Data Strategy

## Development data

Prefer datasets designed for research instead of collecting real personal identity documents.

### Document analysis

**MIDV-500** is a relevant research dataset for identity-document analysis and recognition, including video clips and ground truth for multiple document types. It can support document localization, recognition and related experimentation.

### Document tampering

**DocTamper** is a relevant research dataset for tampered document text detection. Its repository states that the released dataset is for non-commercial use and has access/use requirements, so licensing must be checked before use.

### Face anti-spoofing

**CelebA-Spoof** is a large-scale face anti-spoofing dataset. It is research-oriented and has non-commercial-use restrictions.

### Face manipulation / deepfake research

**FaceForensics++** is a benchmark for manipulated facial imagery and video. Access is controlled by its terms of use.

### Synthetic data

For the demo, create synthetic cases containing:

- fake names
- fake document IDs
- synthetic watchlist records
- simulated device IDs
- controlled duplicate faces/embeddings
- generated tampering examples

**Never upload real Aadhaar/passport/identity records into the development repository.**

---

# 11. External API Strategy

The demo should remain functional without depending on restricted government APIs.

## Local-first APIs

```text
FastAPI
Ollama HTTP API
PostgreSQL/SQLite
Redis (optional)
```

Ollama local endpoint:

```text
http://localhost:11434
```

Example conceptual call:

```http
POST /api/chat
```

## Future integrations

Government or trusted third-party verification APIs can be added through adapters only after formal access/authorization is available.

```text
VerificationProvider
       |
       +--> DemoProvider
       +--> GovernmentProvider
       +--> EnterpriseProvider
```

This prevents the core architecture from becoming dependent on one unavailable external API.

---

# 12. Security Architecture

## Authentication

- JWT/access-token style development scaffold
- Production OAuth2/OIDC
- short-lived tokens
- refresh strategy where required

## RBAC

Roles:

```text
OFFICER
ADMIN
AUDITOR
```

Example permissions:

```text
OFFICER -> create/review cases
ADMIN   -> manage users/configuration
AUDITOR -> audit verification/read-only evidence
```

## Data protection

- TLS in production
- field-level encryption for selected PII
- encryption key from environment/secret manager
- no secrets in source control
- strict logging rules
- avoid raw biometric values in normal logs

## Abuse protection

- rate limiting
- file-size limits
- MIME/content validation
- antivirus/malware scanning hook
- request IDs
- audit trails for sensitive lookups

---

# 13. Database Concept

Core tables/collections:

```text
users
roles
cases
case_files
ocr_results
tamper_results
liveness_results
face_results
validation_results
anomaly_results
risk_scores
audit_events
watchlist_records
device_signals
```

Sensitive fields should be minimized, encrypted where appropriate, and separated from analytical metadata.

---

# 14. Project Structure

Target structure:

```text
identity-screening-system/
|
+-- backend/
|   +-- main.py
|   +-- config.py
|   +-- models/
|   |   +-- schemas.py
|   +-- api/
|   |   +-- routes.py
|   +-- pipeline/
|   |   +-- preprocessing.py
|   |   +-- ocr_extraction.py
|   |   +-- tampering_detection.py
|   |   +-- liveness_detection.py
|   |   +-- validation.py
|   |   +-- face_verification.py
|   |   +-- anomaly_detection.py
|   |   +-- risk_scoring.py
|   |   +-- orchestrator.py
|   +-- blockchain/
|   |   +-- audit_chain.py
|   +-- security/
|   |   +-- auth.py
|   |   +-- encryption.py
|   +-- db/
|       +-- database.py
|
+-- frontend/
|   +-- index.html
|   +-- styles.css
|   +-- app.js
|
+-- data/
|   +-- synthetic/
|   +-- samples/
|
+-- tests/
|
+-- docker-compose.yml
+-- .env.example
+-- README.md
```

---

# 15. Development Phases

We will build this **incrementally**. Do not jump directly into advanced models.

## Phase 1 — Architecture & Project Foundation **[CURRENT]**

### Goal

Convert the architecture into a concrete technical specification that the whole team can follow.

### Tasks

- Freeze the system architecture
- Define modules/services
- Define request/response contracts
- Define case lifecycle
- Define roles and permissions
- Define database entities
- Define API surface
- Define model responsibilities
- Define data strategy
- Define local-vs-production boundaries
- Create repository structure
- Create `.env.example`
- Create base README

### Deliverables

```text
Architecture document
API contract
Data model
Folder structure
README
Development checklist
```

### Exit condition

Everyone can answer:

> What enters the system, which service handles it, what it produces, where it is stored, how it affects risk, and how it becomes auditable?

---

## Phase 2 — Backend Skeleton

Build:

- FastAPI app
- config
- schemas
- health endpoint
- authentication scaffold
- RBAC middleware
- case creation
- file upload
- database connection

Exit condition:

```text
POST /cases -> case_id
GET /health -> OK
```

---

## Phase 3 — End-to-End Mock Pipeline

Implement all stages with deterministic test outputs.

Goal:

```text
Upload -> Screening -> Risk Score -> Audit Chain -> Dashboard
```

This is the first complete demo milestone.

---

## Phase 4 — Real OCR + Preprocessing

Integrate:

- OpenCV
- document detection/cropping
- PaddleOCR/Tesseract
- field normalization
- confidence handling

---

## Phase 5 — Real Face Verification + Liveness

Integrate:

- face detection
- alignment
- ArcFace/InsightFace embeddings
- similarity thresholding
- anti-spoof model

Evaluate latency and false positives/negatives on controlled test data.

---

## Phase 6 — Tampering Detection

Start simple:

```text
ELA + image statistics + suspicious region checks
```

Then evaluate a learned detector using permitted research data.

---

## Phase 7 — Cross-Case Anomaly Detection

Add:

- duplicate identity detection
- device velocity
- repeated submission patterns
- vector similarity search

Upgrade storage from simple rules to Redis/FAISS/pgvector where useful.

---

## Phase 8 — Risk Engine + Explainability

Finalize:

- normalized signals
- weights
- thresholds
- reason codes
- explanation format
- officer decision-support UI

No unexplained single-number output.

---

## Phase 9 — Blockchain / Audit Hardening

Start with a verified cryptographic hash chain.

Then evaluate:

```text
In-memory chain
        -> persistent audit store
        -> permissioned ledger anchor
```

Potential production target: Hyperledger Fabric.

---

## Phase 10 — Security & Production Hardening

Add:

- proper OAuth2/OIDC
- secret management
- encryption
- rate limiting
- validation
- secure headers
- audit access control
- structured logs
- monitoring
- backup/recovery plan

---

## Phase 11 — Demo, Testing & SIH Presentation

Prepare:

- 3–5 scripted cases
- genuine case
- tampered document case
- face mismatch case
- spoof/liveness case
- cross-case fraud case

Demonstration storyline:

```text
1. Officer logs in
2. Creates a case
3. Uploads document + live capture
4. Screening pipeline runs
5. Parallel checks execute
6. Risk score is generated
7. Dashboard explains every signal
8. Officer reviews evidence
9. Audit chain is verified
10. Tampering in the audit store is simulated
11. Chain integrity check detects the break
```

---

# 16. Definition of Done

The project is considered demo-ready when:

- case creation works
- files can be uploaded safely
- pipeline runs end-to-end
- OCR output is visible
- tampering result is visible
- liveness result is visible
- face comparison is visible
- anomaly result is visible
- risk score is explainable
- RBAC works
- sensitive data is not exposed in logs
- audit chain can be verified
- dashboard is usable without manual database edits
- at least one realistic fraud scenario is demonstrated

---

# 17. Team Development Rule

We will work **one phase at a time**.

For every phase we will follow:

```text
PLAN
  -> FILE STRUCTURE
  -> IMPLEMENT
  -> RUN
  -> TEST
  -> FIX
  -> VERIFY
  -> MOVE TO NEXT PHASE
```

No advanced model should be integrated until the interface it plugs into is stable.

---

# 18. Current Status

## Phase 1 — Architecture & Foundation

**Status: STARTING**

Immediate work:

1. Freeze architecture.
2. Define backend modules.
3. Define case schema.
4. Define API contract.
5. Define role/permission matrix.
6. Define model/data boundaries.
7. Create initial repository structure.
8. Then move to the backend skeleton.

---

# 19. Important Technical Notes

- Mock detectors must be clearly labeled as mocks in code and UI.
- Risk score is a decision-support mechanism, not a legal identity verdict.
- Real PII should not be committed to GitHub.
- Model and dataset licenses must be checked before redistribution or deployment.
- Government-only verification integrations should remain adapter interfaces until authorized access exists.
- The final system should preserve the ability to run locally for development and judging.

---

# 20. Reference Technology Stack

```text
Frontend       : HTML + CSS + JavaScript
Backend        : Python + FastAPI
Database       : PostgreSQL (SQLite for very early local prototype)
Cache          : Redis (later)
Vector Search  : FAISS / pgvector (later)
OCR            : PaddleOCR / Tesseract
Vision         : OpenCV + PyTorch
Face           : InsightFace / ArcFace
LLM            : Ollama + Qwen3.5 local model
Auth           : JWT scaffold -> OAuth2/OIDC
Encryption     : Fernet/helper + proper key management in production
Audit          : SHA-256 hash chain -> permissioned ledger later
Containers     : Docker / Docker Compose
Scale          : Kubernetes + message queue later
Testing        : Pytest + API/integration tests
```

---

## 21. The One-Sentence Product Definition

> **A secure, explainable, multi-signal identity-screening platform that detects document manipulation, presentation attacks and cross-case fraud while preserving a tamper-evident audit trail for authorized officers.**

---

## Phase 1 working principle

**First make the architecture undeniable. Then make the pipeline work. Then replace mocks with real models one by one.**
