# PHASE 5 — Final AI, Security, Blockchain & Production Integration

## Goal

Phase 5 is the **final development phase**.

The purpose is to replace the remaining mock intelligence from Phase 3,
integrate the real components developed in Phase 4, complete the security and
audit architecture, and deliver a complete SIH-ready screening system.

After Phase 5, there is **no new architecture phase**.

Post-Phase-5 work is limited to:

```text
bug fixing
threshold/model tuning
performance optimization
documentation
deployment
demo preparation
presentation preparation
```

---

# 1. Final System

```text
                         CLIENT APPS
                             |
                             v
                    API GATEWAY / FASTAPI
                             |
                  ┌──────────┴──────────┐
                  |                     |
                 AUTH                  RATE
                 RBAC                 LIMIT
                  |                     |
                  └──────────┬──────────┘
                             |
                             v
                     CASE ORCHESTRATOR
                             |
                             v
                    DOCUMENT PREPROCESSING
                             |
              ┌──────────────┼──────────────┐
              |              |              |
              v              v              v
             OCR         TAMPERING       LIVENESS
              |              |              |
              └──────────────┼──────────────┘
                             |
                             v
                        VALIDATION
                             |
                             v
                    FACE VERIFICATION
                             |
                             v
                    DEEPFAKE SIGNAL
                             |
                             v
                 ANOMALY / FRAUD ENGINE
                             |
                             v
                       RISK ENGINE
                             |
                ┌────────────┴─────────────┐
                |                          |
                v                          v
          OLLAMA EXPLANATION          AUDIT SERVICE
                |                          |
                |                    HASH-CHAIN / LEDGER
                |                          |
                └────────────┬─────────────┘
                             v
                      OFFICER DASHBOARD
```

---

# 2. Phase 5 Objectives

```text
[ ] Replace remaining AI mocks
[ ] Integrate real face verification
[ ] Integrate real liveness / anti-spoofing
[ ] Integrate tampering detection
[ ] Add deepfake detection
[ ] Build cross-case anomaly detection
[ ] Calibrate risk scoring
[ ] Integrate Ollama explanation layer
[ ] Harden authentication and RBAC
[ ] Add field-level encryption
[ ] Finalize immutable audit chain
[ ] Add production database/vector/velocity components
[ ] Harden dashboard
[ ] Complete testing
[ ] Produce repeatable SIH demo
```

---

# 3. Real vs Mock Status

At the beginning of Phase 5:

```text
REAL
├── document preprocessing
└── OCR

MOCK
├── tampering
├── liveness
├── face verification
├── anomaly detection
└── some audit infrastructure
```

Target at the end:

```text
REAL / PRODUCTION-SHAPED
├── preprocessing
├── OCR
├── tampering
├── liveness
├── deepfake signal
├── face verification
├── anomaly detection
├── deterministic risk engine
├── Ollama explanation
├── authentication/RBAC
├── encryption
├── audit hash chain
└── officer dashboard
```

---

# 4. Phase 5A — Face Verification

## Objective

Replace the mock face verifier.

Target stack:

```text
InsightFace
ArcFace embeddings
OpenCV
NumPy
```

Flow:

```text
Document Image
      |
      v
Document Face Detection
      |
      v
Face Alignment
      |
      v
ArcFace Embedding
      |
      ├───────────────┐
      |               |
      v               v
Reference Face     Live Capture Face
Embedding          Embedding
      |               |
      └───────┬───────┘
              v
        Similarity Score
              |
              v
     Verification Result
```

Output:

```json
{
  "stage": "face_verification",
  "status": "completed",
  "similarity": 0.87,
  "match": true,
  "model": "insightface"
}
```

## Important

Do not hard-code a production threshold from a random example.

Threshold selection must be evaluated using the project test set.

Record:

```text
false accept rate
false reject rate
threshold
dataset
model version
```

---

# 5. Phase 5B — Liveness / Anti-Spoofing

## Objective

Replace the liveness mock with an actual face presentation-attack detector.

Pipeline:

```text
Live Capture / Frames
        |
        v
Face Detection
        |
        v
Face Crop / Alignment
        |
        v
Anti-Spoof Model
        |
        ├── live
        ├── print
        ├── replay
        └── other spoof
```

Output:

```json
{
  "stage": "liveness",
  "status": "completed",
  "liveness_score": 0.94,
  "spoof_score": 0.06,
  "attack_type": "unknown"
}
```

Possible development data:

```text
CelebA-Spoof
OULU-NPU
controlled local capture samples
```

Dataset/model licensing must be checked before redistribution or production use.

---

# 6. Phase 5C — Deepfake Detection

Deepfake detection is a separate signal from liveness.

Concept:

```text
Face / video frames
        |
        v
Temporal / spatial preprocessing
        |
        v
Deepfake detector
        |
        v
Synthetic/manipulation score
```

Output:

```json
{
  "stage": "deepfake",
  "status": "completed",
  "deepfake_score": 0.72,
  "suspected": true
}
```

Development data candidate:

```text
FaceForensics++
```

Keep deepfake detection independent from anti-spoofing so the dashboard can
show why a case received each signal.

---

# 7. Phase 5D — Document Tampering

Replace the Phase 3 mock.

Initial practical architecture:

```text
Document
   |
   ├── ELA / image-forensics signals
   ├── region inconsistency checks
   ├── OCR/layout consistency
   └── learned detector
          |
          v
   Tampering Evidence
```

Possible research data:

```text
DocTamper
synthetically modified document images
```

Output:

```json
{
  "stage": "tampering",
  "status": "completed",
  "tampering_score": 0.81,
  "suspected": true,
  "signals": [
    {
      "type": "text_region_inconsistency",
      "severity": "high"
    }
  ]
}
```

The system should preserve evidence/signals, not only a binary decision.

---

# 8. Phase 5E — Cross-Case Anomaly Detection

This is one of the major SIH differentiators.

## Inputs

```text
case_id
identity/document identifiers
face representation
device fingerprint
IP hash
submission timestamp
prior case history
```

## Signals

```text
same face across identities
same document across identities
same device across many identities
submission velocity
repeated suspicious combinations
```

## Initial architecture

```text
Case Event
    |
    ├── PostgreSQL
    |
    ├── Redis
    |
    └── Vector Index
             |
             v
       Similarity Search
             |
             v
      Fraud Pattern Engine
```

Possible technologies:

```text
PostgreSQL
Redis
FAISS or pgvector
```

Do not store raw biometrics unnecessarily.

Prefer:

```text
derived representations
hashed identifiers
encrypted PII
```

---

# 9. Face Reuse Detection

Example:

```text
New face embedding
       |
       v
Vector search
       |
       v
similar previous embeddings
       |
       v
different identity metadata
       |
       v
FACE_REUSE signal
```

Example output:

```json
{
  "type": "face_reuse",
  "severity": "high",
  "related_cases": [
    "CASE-000013",
    "CASE-000031"
  ]
}
```

The dashboard should show related cases only to users with sufficient
permissions.

---

# 10. Device Velocity Detection

Example:

```text
Device Hash D001
       |
       v
submissions in rolling window
       |
       v
count > configured threshold
       |
       v
VELOCITY_ANOMALY
```

Use Redis later for efficient rolling-window counters.

Prototype fallback:

```text
database query
```

---

# 11. Duplicate Document Detection

Compute:

```text
document cryptographic hash
```

and optionally a content/perceptual fingerprint.

Distinguish:

```text
exact duplicate
near duplicate
different document with similar visual structure
```

Do not use a cryptographic hash as a near-duplicate detector.

---

# 12. Risk Engine

The final risk engine should remain deterministic and explainable.

Example signal groups:

```text
Document
  ├── OCR confidence / inconsistency
  ├── tampering
  └── validation

Biometric
  ├── liveness
  ├── deepfake
  └── face verification

Fraud
  ├── face reuse
  ├── device reuse
  └── velocity
```

Example conceptual weighting:

```text
OCR / validation        10
Tampering               25
Liveness                20
Face verification       20
Deepfake                10
Anomaly                 15
                         ---
                        100
```

These values are initial prototype parameters only.

They must be calibrated and evaluated using the project's validation data.

---

# 13. Risk Score Requirements

Every risk result must include:

```json
{
  "risk_score": 67,
  "risk_level": "high",
  "signals": [
    {
      "code": "TAMPERING",
      "contribution": 20
    },
    {
      "code": "FACE_MISMATCH",
      "contribution": 20
    }
  ]
}
```

The UI must be able to answer:

> Why did this case receive this score?

---

# 14. Missing Signal Handling

Never interpret:

```text
model failed
```

as:

```text
safe
```

Example:

```json
{
  "stage": "liveness",
  "status": "failed",
  "error_code": "MODEL_UNAVAILABLE"
}
```

Risk engine should explicitly account for unavailable signals.

---

# 15. Ollama Explanation Layer

## Role

Ollama receives structured evidence and creates an officer-friendly
explanation.

Input:

```json
{
  "risk_score": 67,
  "risk_level": "high",
  "signals": [
    "TAMPERING",
    "FACE_MISMATCH",
    "DEVICE_REUSE"
  ],
  "stage_results": {}
}
```

Output:

```json
{
  "summary": "The case contains multiple verification concerns.",
  "reasons": [
    "Document tampering indicators were detected.",
    "The captured face did not sufficiently match the document face.",
    "The submission device was associated with multiple cases."
  ]
}
```

## Rules

Ollama must NOT:

```text
set the numeric risk score
approve a case
reject a case
change evidence
override model results
override validation
```

It is an explanation/interface layer.

---

# 16. Ollama Model Strategy

The LLM adapter must be model-agnostic.

Configuration:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:4b
```

The project should support:

```text
local Ollama model
future alternate model
```

through configuration rather than hard-coded model names.

---

# 17. Security Hardening

## Authentication

Development:

```text
dev-token
```

must be disabled in production.

Production target:

```text
OAuth2 / OIDC
     |
     v
Identity Provider
     |
     v
JWT
     |
     v
RBAC
```

---

# 18. RBAC

Final roles:

```text
officer
admin
auditor
```

Access examples:

| Action | Officer | Admin | Auditor |
|---|---:|---:|---:|
| Create case | Yes | Yes | No |
| Upload evidence | Yes | Yes | No |
| Run screening | Yes | Yes | No |
| View screening result | Yes | Yes | Yes |
| View audit chain | Limited | Yes | Yes |
| Verify chain | No | Yes | Yes |
| Manage users | No | Yes | No |
| Change audit records | No | No | No |

Authorization must be checked server-side.

---

# 19. Field-Level Encryption

PII fields should be encrypted at rest.

Candidates:

```text
cryptography
Fernet
```

Encrypt fields such as:

```text
identity-related values
addresses
sensitive document metadata
```

Do not encrypt fields that must remain searchable without designing an
appropriate searchable-encryption or tokenization strategy.

Never place encryption keys in source code.

---

# 20. File Security

Final upload process:

```text
Upload
  |
  v
MIME validation
  |
  v
Magic/content validation
  |
  v
Size validation
  |
  v
Virus/malware scanning hook
  |
  v
SHA-256
  |
  v
Generated internal file ID
  |
  v
Protected storage
```

User filenames must never determine storage paths directly.

---

# 21. Blockchain Audit Layer

The audit chain must become a first-class service.

## Event model

```json
{
  "event_id": "EVT-001",
  "case_id": "CASE-001",
  "stage": "ocr",
  "timestamp": "...",
  "actor_id": "officer_001",
  "result_hash": "...",
  "previous_hash": "...",
  "current_hash": "..."
}
```

Hash:

```text
current_hash =
SHA256(
    event_payload
    + previous_hash
)
```

---

# 22. What Goes Into the Ledger

Store:

```text
case identifier
event identifier
timestamp
stage
actor/reference
result hash
previous hash
current hash
```

Do NOT store:

```text
raw document image
raw face image
full PII
encryption keys
JWT
```

---

# 23. Chain Verification

API:

```http
GET /api/v1/cases/{case_id}/audit
```

and:

```http
POST /api/v1/audit/verify
```

Response:

```json
{
  "valid": true,
  "checked_events": 14,
  "first_broken_event": null
}
```

Tampering simulation must produce:

```json
{
  "valid": false,
  "first_broken_event": "EVT-009"
}
```

---

# 24. Permissioned Blockchain Adapter

The current hash chain remains the application's audit abstraction.

Create a ledger interface:

```python
class AuditLedger:
    def append(self, event): ...
    def verify(self): ...
```

Implement:

```text
LocalHashChainLedger
```

Later adapter:

```text
HyperledgerFabricLedger
```

This keeps the application independent of the underlying ledger technology.

---

# 25. PostgreSQL

Move the production-shaped database from SQLite to PostgreSQL.

Suggested logical entities:

```text
users
cases
files
screening_runs
pipeline_results
identities
devices
fraud_signals
watchlist_entries
officer_decisions
audit_events
```

Do not store raw images inside normal relational tables unless there is a
specific reason.

Prefer object storage for large files.

---

# 26. Vector Search

Use one vector layer for reusable face/feature similarity.

Possible:

```text
FAISS
```

or:

```text
PostgreSQL + pgvector
```

Initial use:

```text
face embedding similarity
duplicate/near-duplicate feature search
```

Store references to the case rather than unnecessary raw biometric data.

---

# 27. Redis

Use Redis primarily for:

```text
submission velocity
rate limiting
short-lived counters
temporary pipeline state
```

Example:

```text
velocity:{device_hash}:5m
velocity:{ip_hash}:1h
```

Do not use Redis as the authoritative case database.

---

# 28. Dashboard — Final

Dashboard sections:

```text
1. Login
2. Case creation
3. Evidence upload
4. Screening execution
5. Overall result
6. Risk score
7. Stage breakdown
8. Evidence/field comparison
9. Fraud signals
10. Related cases
11. Audit trail
12. Blockchain verification
```

---

# 29. Officer Result Screen

The officer should see:

```text
CASE-001
--------------------------------

Risk Score
67 / 100

Risk Level
HIGH

--------------------------------

Document
✓ OCR completed
⚠ Tampering signal

Biometric
✗ Face mismatch
✓ Liveness passed
⚠ Deepfake signal

Cross-case
⚠ Device reused
⚠ Related cases

--------------------------------

WHY?
[explanation]

--------------------------------

AUDIT
14 events
Chain: VALID
```

The UI should display evidence and explanations separately.

---

# 30. Officer Decision

The system produces:

```text
screening result
```

The officer may then record:

```text
reviewed
additional_review_required
cleared
escalated
```

The AI system should not silently convert a risk score into an official
government action.

Officer decisions must themselves generate audit events.

---

# 31. Data Retention

Create configurable retention settings:

```text
raw upload retention
processed image retention
screening result retention
audit retention
```

Do not hard-code a real government retention period without an approved policy.

---

# 32. Monitoring

Track:

```text
request latency
pipeline latency
per-stage latency
model failures
OCR failures
liveness failures
queue/backlog
database latency
CPU/GPU usage
```

Do not expose sensitive PII in monitoring logs.

---

# 33. Observability

Every request should have:

```text
request_id
case_id
screening_run_id
stage
status
duration
error_code
```

This allows:

```text
Dashboard issue
      ↓
screening_run_id
      ↓
stage
      ↓
log
```

---

# 34. API Finalization

Required APIs:

## Authentication

```text
POST /api/v1/auth/login
```

or the future OIDC integration.

Development-only:

```text
POST /api/v1/auth/dev-token
```

must be disabled outside development.

## Cases

```text
POST /api/v1/cases
GET  /api/v1/cases
GET  /api/v1/cases/{case_id}
```

## Files

```text
POST /api/v1/cases/{case_id}/files
GET  /api/v1/cases/{case_id}/files
```

## Screening

```text
POST /api/v1/cases/{case_id}/screen
GET  /api/v1/cases/{case_id}/screening/latest
GET  /api/v1/cases/{case_id}/screening/{run_id}
```

## Audit

```text
GET  /api/v1/cases/{case_id}/audit
POST /api/v1/audit/verify
```

## Health

```text
GET /api/v1/health
GET /api/v1/health/dependencies
```

---

# 35. Final API Response

A completed screening should expose one stable response:

```json
{
  "case_id": "CASE-000001",
  "screening_run_id": "RUN-000001",
  "status": "completed",

  "risk": {
    "score": 67,
    "level": "high"
  },

  "stages": {
    "preprocessing": {},
    "ocr": {},
    "tampering": {},
    "liveness": {},
    "validation": {},
    "face_verification": {},
    "deepfake": {},
    "anomaly": {}
  },

  "explanation": {
    "summary": "...",
    "reasons": []
  },

  "audit": {
    "event_count": 14,
    "chain_valid": true
  }
}
```

---

# 36. Test Dataset Strategy

Final test set should contain:

```text
clean cases
blurred documents
rotated documents
low-light documents
tampered documents
spoof attempts
deepfake examples
face mismatches
reused face patterns
reused device patterns
high-velocity patterns
pipeline failures
```

Create a fixed:

```text
data/evaluation/final/
```

Do not repeatedly tune the system against the final test set.

---

# 37. End-to-End Test Scenarios

## Test 1 — Genuine case

```text
Good preprocessing
Good OCR
No tampering
Live
No deepfake
Face match
No anomaly
```

Expected:

```text
low-risk prototype result
```

---

## Test 2 — Tampered document

```text
Good preprocessing
Good OCR
Tampering detected
Live
Face match
```

Expected:

```text
tampering signal
higher risk
```

---

## Test 3 — Face mismatch

```text
Valid document
Clean tampering
Live
Face mismatch
```

Expected:

```text
biometric signal
higher risk
```

---

## Test 4 — Presentation attack

```text
Valid document
Clean document
Spoof detected
```

Expected:

```text
liveness failure
```

---

## Test 5 — Deepfake

```text
Document valid
Liveness result available
Deepfake signal high
```

Expected:

```text
deepfake signal shown separately
```

---

## Test 6 — Coordinated fraud

```text
Face reused
Device reused
High velocity
```

Expected:

```text
multiple anomaly signals
related cases displayed
```

---

# 38. Failure Tests

Intentionally simulate:

```text
OCR unavailable
tampering model unavailable
liveness model unavailable
face model unavailable
database unavailable
Ollama unavailable
audit service unavailable
```

The API must return meaningful states instead of silently marking a case as
safe.

---

# 39. Security Tests

Test:

```text
[ ] invalid JWT
[ ] expired JWT
[ ] wrong role
[ ] unauthorized case access
[ ] path traversal upload
[ ] oversized file
[ ] invalid MIME
[ ] corrupted file
[ ] audit manipulation
[ ] unauthorized audit access
[ ] sensitive data in logs
```

---

# 40. Performance Tests

Measure:

```text
upload latency
preprocessing latency
OCR latency
tampering latency
liveness latency
face latency
anomaly latency
total screening latency
```

Also measure GPU-heavy model behaviour separately.

Do not claim benchmark values without recording actual measurements.

---

# 41. Docker / Production Layout

Target:

```text
docker-compose.yml
```

Services:

```text
api
postgres
redis
ollama
frontend
```

Optional later:

```text
worker
vector-store
object-storage
```

Kubernetes remains an optional deployment target, not a prerequisite for the
SIH demo.

---

# 42. Environment

Production configuration should include:

```env
APP_ENV=production

DATABASE_URL=...

JWT_SECRET=...
ENCRYPTION_KEY=...

REDIS_URL=...

OLLAMA_BASE_URL=...
OLLAMA_MODEL=...

OBJECT_STORAGE_URL=...

AUDIT_LEDGER_MODE=hashchain
```

Secrets must come from:

```text
environment
secret manager
deployment platform secrets
```

Never from source code.

---

# 43. Final Repository Structure

```text
identity-screening-system/
│
├── backend/
│   ├── main.py
│   ├── config.py
│   │
│   ├── api/
│   │   ├── routes.py
│   │   ├── auth_routes.py
│   │   ├── screening_routes.py
│   │   └── audit_routes.py
│   │
│   ├── models/
│   │   └── schemas.py
│   │
│   ├── document/
│   │   ├── preprocessing.py
│   │   ├── quality.py
│   │   ├── document_detector.py
│   │   ├── perspective.py
│   │   ├── normalization.py
│   │   └── mrz_parser.py
│   │
│   ├── pipeline/
│   │   ├── orchestrator.py
│   │   ├── preprocessing.py
│   │   ├── ocr_extraction.py
│   │   ├── tampering_detection.py
│   │   ├── liveness_detection.py
│   │   ├── deepfake_detection.py
│   │   ├── validation.py
│   │   ├── face_verification.py
│   │   ├── anomaly_detection.py
│   │   └── risk_scoring.py
│   │
│   ├── ai/
│   │   ├── ocr/
│   │   ├── face/
│   │   ├── liveness/
│   │   ├── tampering/
│   │   ├── deepfake/
│   │   └── ollama/
│   │
│   ├── fraud/
│   │   ├── face_reuse.py
│   │   ├── device_velocity.py
│   │   └── duplicate_detection.py
│   │
│   ├── blockchain/
│   │   ├── interface.py
│   │   ├── audit_chain.py
│   │   └── hyperledger_adapter.py
│   │
│   ├── security/
│   │   ├── auth.py
│   │   ├── rbac.py
│   │   └── encryption.py
│   │
│   ├── db/
│   │   ├── database.py
│   │   ├── models.py
│   │   └── repositories/
│   │
│   ├── services/
│   │   ├── case_service.py
│   │   ├── screening_service.py
│   │   ├── file_service.py
│   │   └── audit_service.py
│   │
│   └── utils/
│
├── frontend/
│   └── index.html
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── synthetic/
│   └── evaluation/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── e2e/
│
├── docker/
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

# 44. Implementation Order Inside Phase 5

Do NOT build everything simultaneously.

Use this exact order:

```text
5.1  Face verification
      ↓
5.2  Liveness / anti-spoofing
      ↓
5.3  Tampering detector
      ↓
5.4  Deepfake detector
      ↓
5.5  Cross-case anomaly engine
      ↓
5.6  Risk calibration
      ↓
5.7  Ollama explanation service
      ↓
5.8  PostgreSQL + Redis + vector layer
      ↓
5.9  Security hardening
      ↓
5.10 Final hash-chain audit layer
      ↓
5.11 Final dashboard
      ↓
5.12 Integration testing
      ↓
5.13 Security testing
      ↓
5.14 Performance testing
      ↓
5.15 SIH demo freeze
```

---

# 45. Phase 5 Definition of Done

Phase 5 is complete only when:

```text
[ ] Real preprocessing works
[ ] Real OCR works
[ ] Real tampering detection works
[ ] Real liveness detection works
[ ] Deepfake signal works
[ ] Real face verification works
[ ] Cross-case anomaly engine works
[ ] Risk engine is deterministic and explainable
[ ] Ollama explanation works
[ ] Authentication works
[ ] RBAC works
[ ] PII encryption works
[ ] Upload security works
[ ] Audit hash chain works
[ ] Audit chain verification works
[ ] PostgreSQL integration works
[ ] Redis integration works where required
[ ] Vector similarity works where required
[ ] Officer dashboard is integrated
[ ] Failure states are handled correctly
[ ] Unit tests pass
[ ] Integration tests pass
[ ] Security tests pass
[ ] End-to-end tests pass
[ ] Demo scenarios are repeatable
[ ] Docker deployment works
```

---

# 46. Final SIH Demo Flow

The final demo should be able to show:

```text
OFFICER LOGIN
      ↓
CREATE CASE
      ↓
UPLOAD DOCUMENT + LIVE CAPTURE
      ↓
RUN SCREENING
      ↓
PREPROCESSING
      ↓
OCR
      ↓
TAMPERING + LIVENESS
      ↓
VALIDATION
      ↓
FACE VERIFICATION
      ↓
DEEPFAKE SIGNAL
      ↓
CROSS-CASE ANOMALY
      ↓
RISK SCORE
      ↓
OLLAMA EXPLANATION
      ↓
AUDIT HASH CHAIN
      ↓
OFFICER REVIEW
      ↓
VERIFY AUDIT INTEGRITY
```

---

# 47. What the Judges Should Be Able to See

The final system should demonstrate four clear ideas:

## 1. Document fraud

```text
Is the document itself suspicious?
```

## 2. Presentation / biometric fraud

```text
Is the presenter live?
Is the face genuine?
Does the face match?
```

## 3. Coordinated fraud

```text
Does this case connect to suspicious previous activity?
```

## 4. Trustworthy audit

```text
Can we prove what happened during verification?
```

---

# 48. Final Architecture Principle

The final product is NOT:

```text
one giant AI model
```

It is:

```text
specialized detectors
        +
deterministic validation
        +
cross-case intelligence
        +
explainable risk scoring
        +
secure APIs
        +
tamper-evident audit
```

Each component can be independently replaced or upgraded.

---

# 49. Final Phase Boundary

After this phase:

```text
NO new pipeline stage
NO new core architecture
NO major technology rewrite
```

Only:

```text
fix
test
tune
optimize
document
deploy
present
```

---

# PHASE 5 SUCCESS CRITERION

A complete case can enter the system and produce:

```text
evidence
   ↓
real document processing
   ↓
real multi-signal verification
   ↓
cross-case fraud analysis
   ↓
explainable deterministic risk
   ↓
human-readable explanation
   ↓
tamper-evident audit trail
   ↓
officer decision
```

with every important operation:

```text
authenticated
authorized
logged
traceable
and integrity-verifiable
```

This is the final development target for SIH26188.
