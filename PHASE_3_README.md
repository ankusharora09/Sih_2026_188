# Phase 3 — Complete Mock Verification Pipeline

## Goal

Phase 3 connects the backend foundation from Phase 2 into one complete,
end-to-end identity screening pipeline.

At the end of this phase, a case should be able to travel through every
verification stage and produce one structured screening result.

**Important:** AI-heavy stages are still mocks in this phase. The purpose is
to prove the architecture, contracts, orchestration, error handling, audit
events, and dashboard flow before introducing real models.

---

# 1. Phase 3 Outcome

The working flow becomes:

```text
Case + Uploaded Evidence
          |
          v
    Preprocessing
          |
          v
 ┌────────┼───────────────┐
 |        |               |
 v        v               v
 OCR   Tampering       Liveness
 |        |               |
 └────────┼───────────────┘
          |
          v
      Validation
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
          v
  Complete Case Result
```

The parallel section must run concurrently.

---

# 2. Core Requirement

One API request must be capable of running the complete pipeline:

```http
POST /api/v1/cases/{case_id}/screen
```

Example response:

```json
{
  "case_id": "CASE-000001",
  "status": "completed",
  "risk": {
    "score": 31,
    "level": "medium"
  },
  "stages": [],
  "duration_ms": 1240
}
```

The actual stage results will be populated by the orchestrator.

---

# 3. Stage Order

## Stage 1 — Preprocessing

Purpose:

- validate that usable evidence exists
- inspect image quality
- normalize input metadata
- prepare paths for downstream stages

Current implementation:

```text
mock/simple preprocessing
```

Later:

```text
OpenCV
document detection
deskew
crop
perspective correction
quality enhancement
```

Output:

```json
{
  "stage": "preprocessing",
  "status": "completed",
  "document_detected": true,
  "image_quality": 0.91
}
```

---

# 4. Stage 2A — OCR

For Phase 3, OCR returns deterministic/demo data.

Example:

```json
{
  "stage": "ocr",
  "status": "completed",
  "confidence": 0.96,
  "fields": {
    "name": "DEMO USER",
    "document_number": "DEMO123456",
    "date_of_birth": "2000-01-01",
    "expiry_date": "2030-01-01"
  }
}
```

### Mock behaviour

The mock should support at least:

```text
normal
low_confidence
missing_field
```

This allows us to test downstream validation without a real OCR model.

### Future model

```text
PaddleOCR
```

Fallback:

```text
Tesseract
```

---

# 5. Stage 2B — Tampering Detection

The mock simulates document-forgery analysis.

Output:

```json
{
  "stage": "tampering",
  "status": "completed",
  "tampering_score": 0.18,
  "is_suspected": false,
  "signals": []
}
```

### Mock scenarios

```text
clean
suspicious
high_tampering
```

Example suspicious response:

```json
{
  "stage": "tampering",
  "status": "completed",
  "tampering_score": 0.84,
  "is_suspected": true,
  "signals": [
    {
      "type": "text_region_inconsistency",
      "severity": "high"
    }
  ]
}
```

### Future implementation

Potential components:

```text
OpenCV
ELA
noise analysis
document-forensics model
DocTamper research pipeline
```

---

# 6. Stage 2C — Liveness

This stage represents presentation-attack detection.

Output:

```json
{
  "stage": "liveness",
  "status": "completed",
  "liveness_score": 0.95,
  "spoof_score": 0.05,
  "deepfake_score": 0.02
}
```

### Mock scenarios

```text
live
photo_attack
screen_replay
deepfake
```

### Important distinction

```text
Liveness ≠ Face verification
```

Liveness asks whether the presented face appears to be a live subject.

Face verification asks whether the face corresponds to the enrolled/document identity.

---

# 7. Parallel Execution

OCR, tampering, and liveness must execute concurrently.

Conceptually:

```python
ocr_result, tamper_result, liveness_result = await asyncio.gather(
    run_ocr(...),
    run_tampering(...),
    run_liveness(...)
)
```

This is an architectural requirement, not just an optimization.

The three stages have no dependency on each other's outputs.

---

# 8. Stage 3 — Validation

Validation receives the outputs from preprocessing and OCR.

Checks can include:

```text
required OCR fields
document number format
date format
expiry status
basic field consistency
mock watchlist
```

Example:

```json
{
  "stage": "validation",
  "status": "completed",
  "valid": false,
  "field_mismatches": [
    {
      "field": "document_number",
      "reason": "format mismatch"
    }
  ],
  "warnings": []
}
```

Validation is rule-based.

It should not depend on Ollama.

---

# 9. Stage 4 — Face Verification

The mock compares:

```text
document face
       +
live face frame
```

Output:

```json
{
  "stage": "face_verification",
  "status": "completed",
  "similarity": 0.87,
  "match": true
}
```

### Mock scenarios

```text
strong_match
weak_match
mismatch
```

### Future implementation

```text
InsightFace
ArcFace embeddings
cosine similarity
```

Production thresholds must be calibrated from an evaluated dataset. The
Phase 3 mock values are not production biometric thresholds.

---

# 10. Stage 5 — Anomaly Detection

This stage looks beyond the current document.

Inputs can include:

```text
case
identity hash
document hash
face representation/hash
device hash
IP hash
submission history
```

Output:

```json
{
  "stage": "anomaly",
  "status": "completed",
  "anomaly_score": 0.71,
  "signals": [
    {
      "type": "device_reuse",
      "severity": "medium"
    }
  ]
}
```

### Mock scenarios

```text
normal
reused_face
reused_device
high_velocity
multiple_identity_match
```

The synthetic fraud database from later development will replace these mock
signals.

---

# 11. Stage 6 — Risk Scoring

Risk scoring combines structured evidence.

Example prototype formula:

```text
Risk Score =
    OCR inconsistency      × weight
  + Tampering              × weight
  + Liveness failure       × weight
  + Face mismatch          × weight
  + Anomaly signals        × weight
  + Validation failures    × weight
```

A simple prototype configuration may be:

```text
OCR / validation       → 10
Tampering              → 25
Liveness               → 20
Face verification      → 20
Anomaly detection      → 20
Other validation       → 5
                         ---
                         100
```

These weights are prototype parameters and must not be represented as
official government policy.

### Output

```json
{
  "stage": "risk_scoring",
  "status": "completed",
  "risk_score": 64,
  "risk_level": "high",
  "signals": [
    "tampering_suspected",
    "face_mismatch"
  ]
}
```

Risk scoring is deterministic Python logic.

**Ollama must not decide the final score.**

---

# 12. Ollama Role in Phase 3

Ollama is optional in the first successful pipeline run.

When enabled, its role is:

```text
Structured screening signals
          |
          v
        Ollama
          |
          v
Officer-friendly explanation
```

Example input:

```json
{
  "risk_score": 64,
  "signals": [
    "tampering_suspected",
    "face_mismatch"
  ]
}
```

Example explanation:

```text
The case was flagged because the document showed a
tampering signal and the captured face did not meet
the configured verification threshold.
```

The LLM does not:

```text
set the risk score
approve a case
reject a case
modify evidence
override deterministic checks
```

---

# 13. Pipeline Result Schema

The orchestrator returns one top-level result:

```json
{
  "case_id": "CASE-000001",
  "status": "completed",
  "started_at": "...",
  "completed_at": "...",
  "duration_ms": 1234,

  "stages": {
    "preprocessing": {},
    "ocr": {},
    "tampering": {},
    "liveness": {},
    "validation": {},
    "face_verification": {},
    "anomaly": {},
    "risk_scoring": {}
  },

  "risk": {
    "score": 64,
    "level": "high"
  },

  "explanation": {
    "summary": "...",
    "signals": []
  }
}
```

This structure becomes the main object consumed by the dashboard.

---

# 14. Stage Failure Handling

One failed stage must not crash the entire backend process.

Example:

```text
OCR
 ↓
FAILED
 ↓
status = failed
error_code = OCR_ERROR
```

The orchestrator should decide whether downstream processing can continue.

Example policy:

```text
Preprocessing failure
    → stop

OCR failure
    → validation may become incomplete
    → risk score gets an explicit missing-signal penalty/state

Tampering failure
    → continue with unavailable signal

Liveness failure
    → continue with unavailable signal

Face verification failure
    → mark biometric result unavailable

Anomaly failure
    → continue with anomaly unavailable
```

No failed model may silently become:

```text
false
```

or:

```text
safe
```

A missing detector result must remain distinguishable from a detector result
that actually says the subject/document is safe.

---

# 15. Audit Events

Phase 3 creates structured audit events.

Example:

```json
{
  "event_id": "EVT-001",
  "case_id": "CASE-000001",
  "stage": "ocr",
  "status": "completed",
  "timestamp": "...",
  "result_hash": "..."
}
```

For now these events may be recorded by the audit service/database.

The full hash-chain implementation is hardened in a later phase.

---

# 16. Idempotency

Repeated requests for the same screening should be handled safely.

Example:

```text
POST /cases/CASE-001/screen
```

called twice should not create confusing duplicate executions.

Use an execution identifier such as:

```text
screening_run_id
```

Example:

```json
{
  "screening_run_id": "RUN-000001",
  "case_id": "CASE-000001"
}
```

A later production version can add request idempotency keys.

---

# 17. Execution States

Screening run states:

```text
queued
processing
completed
completed_with_warnings
failed
```

Case status and screening status should remain separate.

Example:

```text
case.status = processing
run.status = completed_with_warnings
```

---

# 18. API

## Run screening

```http
POST /api/v1/cases/{case_id}/screen
```

### Success

```json
{
  "case_id": "CASE-000001",
  "screening_run_id": "RUN-000001",
  "status": "completed",
  "risk_score": 24,
  "risk_level": "low"
}
```

---

## Get screening result

```http
GET /api/v1/cases/{case_id}/screening/{run_id}
```

Returns the complete stage-by-stage result.

---

## Get latest result

```http
GET /api/v1/cases/{case_id}/screening/latest
```

Returns the latest completed screening.

---

# 19. Dashboard Requirements

The Phase 3 dashboard must display:

```text
Case ID
Overall status
Risk score
Risk level

Stage cards:
├── Preprocessing
├── OCR
├── Tampering
├── Liveness
├── Validation
├── Face Verification
└── Anomaly

Explanation
Audit events
Execution time
Warnings/errors
```

The dashboard should prioritize **why** a case received its result instead of
only showing a numeric score.

---

# 20. Demo Scenarios

Create at least five repeatable demo scenarios.

## Scenario A — Clean

```text
OCR            → good
Tampering      → clean
Liveness       → live
Validation     → valid
Face           → match
Anomaly        → normal

Expected:
LOW risk
```

## Scenario B — Document tampering

```text
OCR            → good
Tampering      → suspicious
Liveness       → live
Face           → match
Anomaly        → normal

Expected:
higher risk
```

## Scenario C — Face mismatch

```text
Document       → valid
Tampering      → clean
Liveness       → live
Face           → mismatch
Anomaly        → normal

Expected:
high biometric concern
```

## Scenario D — Spoof attempt

```text
Document       → valid
Tampering      → clean
Liveness       → failed
Face           → match/uncertain
Anomaly        → normal

Expected:
high presentation-attack concern
```

## Scenario E — Coordinated fraud

```text
Document       → valid
Tampering      → clean
Liveness       → live
Face           → match
Anomaly        → reused face/device + high velocity

Expected:
high anomaly concern
```

---

# 21. Mock Data Generator

Create a small deterministic generator so the team can test without manually
uploading evidence every time.

Target:

```text
backend/testing/
    mock_cases.py
```

Generate cases such as:

```text
clean_case
tampered_case
face_mismatch_case
spoof_case
fraud_pattern_case
```

Do not use real personal data.

---

# 22. Testing

Phase 3 tests:

```text
[ ] preprocessing stage
[ ] OCR stage
[ ] tampering stage
[ ] liveness stage
[ ] validation stage
[ ] face verification stage
[ ] anomaly stage
[ ] risk scoring
[ ] orchestrator ordering
[ ] parallel execution
[ ] stage failure handling
[ ] result persistence
[ ] API response
```

At minimum, test:

```text
1 clean case
1 suspicious case
1 failed-stage case
1 complete pipeline run
```

---

# 23. Timing Validation

Because OCR/tampering/liveness should be parallel, verify the behaviour.

For example, if:

```text
OCR        = 300 ms
Tampering  = 300 ms
Liveness   = 300 ms
```

Sequential execution is approximately:

```text
900 ms
```

Parallel execution should be close to:

```text
300 ms + orchestration overhead
```

This is a simple proof that the orchestrator is actually concurrent.

---

# 24. Phase 3 Folder Structure

Target:

```text
backend/
│
├── main.py
├── config.py
│
├── api/
│   ├── routes.py
│   └── dependencies.py
│
├── models/
│   └── schemas.py
│
├── pipeline/
│   ├── contracts.py
│   ├── preprocessing.py
│   ├── ocr_extraction.py
│   ├── tampering_detection.py
│   ├── liveness_detection.py
│   ├── validation.py
│   ├── face_verification.py
│   ├── anomaly_detection.py
│   ├── risk_scoring.py
│   └── orchestrator.py
│
├── services/
│   └── screening_service.py
│
├── db/
│   └── database.py
│
├── security/
│   └── auth.py
│
└── testing/
    └── mock_cases.py

tests/
├── test_preprocessing.py
├── test_parallel_stages.py
├── test_validation.py
├── test_risk_scoring.py
└── test_orchestrator.py
```

---

# 25. Phase 3 Definition of Done

Phase 3 is complete when:

```text
[ ] A case can be screened through one API endpoint
[ ] All eight pipeline stages execute
[ ] OCR/tampering/liveness execute in parallel
[ ] Every stage returns the common contract
[ ] Stage failures are represented explicitly
[ ] Results are persisted
[ ] Risk score is generated deterministically
[ ] Dashboard displays stage-by-stage results
[ ] Audit events are generated
[ ] Demo scenarios are repeatable
[ ] Automated tests pass
[ ] Docker startup still works
```

---

# 26. What We Do NOT Build Yet

Do not introduce production AI models yet:

```text
NO real PaddleOCR integration
NO real tampering model
NO real anti-spoof model
NO real deepfake model
NO real ArcFace integration
NO FAISS
NO Redis
NO Kafka
NO Hyperledger Fabric deployment
```

Those are later phases.

Phase 3 proves that the **system works as a system**.

---

# 27. Phase 3 → Phase 4 Transition

At the end of Phase 3:

```text
Upload
  ↓
Complete mock screening
  ↓
Structured result
  ↓
Dashboard
```

Phase 4 will replace the first group of mocks with real document processing:

```text
Raw document
      ↓
OpenCV preprocessing
      ↓
Document normalization
      ↓
PaddleOCR
      ↓
Structured OCR fields
```

The API and pipeline contracts should remain unchanged.

---

# Phase 3 Deliverables

```text
1. Complete orchestrator
2. All mock stages
3. Parallel OCR/tampering/liveness
4. Deterministic risk engine
5. Screening API
6. Screening result persistence
7. Dashboard integration
8. Audit events
9. Mock scenario generator
10. Automated tests
```

## Success criterion

A demo user can:

```text
Login
  ↓
Create case
  ↓
Upload evidence
  ↓
Run screening
  ↓
Watch pipeline execute
  ↓
Receive risk score
  ↓
See exactly which signals contributed
  ↓
Open the complete structured result
```

That is the minimum complete vertical slice before we begin replacing mocks
with real AI components.
