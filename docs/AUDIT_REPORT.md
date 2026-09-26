# SIH 26188 — Full Project Audit Report

Date: 2026-09-22 · Scope: complete repository, per the Phase 1–22 plan. Everything below was verified by running code, not inferred.

## 1. Architecture Summary (as actually implemented)

```
OFFICER (frontend/client/index.html + dashboard in case_detail_routes)
   ↓ Bearer JWT (HS256, roles: officer/admin/auditor)
FastAPI (backend/main.py: CORS, security headers, rate-limit middleware)
   ↓ POST /cases/{id}/screen → 202 Accepted (enqueue)
screening_service.create_screening_run → worker thread (_execute_run, own DB session)
   ↓ stages committed incrementally (crash-safe), UI polls GET /screening
PREPROCESSING (quality → document detection → perspective → rotation → enhancement)
   ↓
OCR (PaddleOCR, cached singleton → Tesseract fallback) → extract_identity_fields
   ↓
LIVENESS (sharpness+entropy)   TAMPERING (ELA + noise inconsistency, localized regions)
   ↓
FACE VERIFICATION (YuNet detect → SFace 128-d embed → calibrated cosine)
   ↓
DEEPFAKE (FFT spectral + chrominance; honest 'unavailable' without live capture)
   ↓
ANOMALY (duplicate content-hash, reused subject name, reused ID number w/ different name)
   ↓
RISK ENGINE (explainable contributions: value/threshold/reason per signal)
   ↓
EXPLANATION (Ollama optional; deterministic fallback from contribution_details)
   ↓
AUDIT (SHA-256 hash chain per event; /audit/verify integrity endpoint)
```

## 2. Face Mismatch Audit (Phase 2/3)

| Location | Behavior before | Problem | Fix | Test |
|---|---|---|---|---|
| `haar_adapter.py` YuNet `score_threshold=0.3` | Random noise → spurious detection → `match=True, similarity=0.95` | Fabricated matches on non-faces | Raised to 0.6 (OpenCV sample default) | `test_noise_never_matches_itself` |
| `verify()` deep path | `faces_count` hardcoded `2`; multi-face ambiguity silently dropped | Officer never sees multiple-face risk | Real distinct-detection count via `_count_faces_yunet`; `uncertainty="multiple_faces"` + `signals=["multiple_faces_detected"]` | degenerate/uncertainty tests |
| `_calibrate()` below threshold | All weak rejects clamped to a flat 0.20 | Destroyed gradation; 0.30 cosine looked identical to 0.05 | Monotone map `0.20 + 1.515·cos`, still below threshold | `test_calibration_monotone_and_bounded` |
| Grey zone 0.363–0.443 cosine | Forced binary match | No uncertainty band | `uncertainty="uncertain"` + `similarity_near_threshold` signal | calibration boundary tests |
| Fallback embedding path | Used the deep-path 0.70 threshold on an uncalibrated HOG-ish vector | Fallback matches are not comparable to SFace | Dedicated `_FALLBACK_MATCH_THRESHOLD = 0.85`, `uncertainty="uncalibrated_fallback"` | `TestFallbackPath` |
| `setInputSize` per call | Mutated shared detector state; now a cached singleton called from worker threads | Race under concurrent screenings | `threading.Lock` around detect calls | all adapter tests run through singleton |
| `risk/engine.py` face stage | `match=None` (no face) passed silently | Insufficient evidence looked "safe" | `review=True` + `face_analysis_no_face/multiple_faces` reason | live run shows REVIEW_REQUIRED |
| UI badges (dashboard + case detail) | Binary VERIFIED/MISMATCH only | Uncertainty invisible to officer | Amber "⚠ UNCERTAIN — MANUAL REVIEW" badge for multiple_faces/uncalibrated_fallback | code-reviewed, live render |

Honest statement: SFace cosine threshold 0.363 is the official OpenCV value; the 0.75 mapping is a linear calibration **not validated on a real face dataset** — the grey-zone band is deliberately conservative for that reason.

## 3. Bugs Fixed (verified by tests or live run)

1. **Spurious face match on noise** (critical, demo-killing) — threshold 0.3→0.6.
2. **Fabricated `faces_count: 2`** — now real per-image detection counts.
3. **Flat clamp destroyed mismatch gradation** — monotone calibration.
4. **Fallback path borrowed deep-path threshold** — separated, stricter gate.
5. **Detector thread race** (factories became cached singletons in the async refactor) — lock added.
6. **PaddleOCR constructed per request** — cached engine + lock (Tesseract too); pinned by test.
7. **Unauthenticated token minting in prod-like runs** — `AUTH_DEV_TOKEN_ENABLED` gate (default on for dev, explicitly off-able).
8. **Silent uncertainty** in risk engine — no-face/multi-face now forces review.
9. **Missing cross-case ID-reuse signal** (Phase 8) — implemented with "repeated identity signal" wording, no auto-guilt.
10. **Document detector destroyed portrait photos** (found 2026-09-26) — any 4-point Canny contour (e.g. an 85×38 photo-frame strip inside a portrait) was accepted as the "document" and perspective-warped onto, wiping out the face for verification. Now guarded: quad must cover ≥15% of the frame, ≥80 px per side, aspect 0.35–2.6.

## 4. Features Added (all real, no placeholders)

- `uncertainty` field on face results (`none | no_face | multiple_faces | uncertain | uncalibrated_fallback`) + `signals` list + `model_version` tracking in every face result.
- Multi-face risk surfacing through risk engine → review flag → UI badge.
- Cross-case ID-number reuse anomaly (strongest identity signal short of face-embedding reuse).
- Adversarial test suite (18 tests): degenerate inputs, calibration properties, liveness honesty, tampering region shape, deepfake unavailability honesty, OCR caching.
- `model_version` in face results (Phase 19 item 7, minimal honest version).

## 5. Tests

- `tests/unit`: **53 passed** (incl. 18 new adversarial tests, 15 field-extraction tests).
- `tests/integration/test_screening_flow.py`: full 202 → 409 → poll → completed flow, numeric timings — **passed**.
- Live end-to-end (server restarted, PID 35056): two demo cases screened; identity-reuse anomaly fired on case 2 with exact expected wording; `audit_chain_valid=True` on both; OCR extraction and name cross-check working.
- 2026-09-26 update: full suite now **107 passed** (incl. 10 new tests for the trained deepfake adapter and face-reuse persistence). Live E2E re-verified: trained classifier scored aligned face crops (`crop_source=yunet_sface_aligned`), FACE_REUSE anomaly fired on the second duplicate-face case (cosine 1.0), audit chain valid.

## 6. Remaining Problems (genuine, unresolved)

- **Liveness is NOT presentation-attack detection.** Sharpness+entropy rejects flat/blank images only. A printed photo with texture passes. Documented in tests; do not demo it as anti-spoofing.
- **Deepfake classifier trained on synthetic faces only.** The ResNet18 checkpoint (`models/document_forgery_gt2.pth`, wired in 2026-09-26) reaches 100% on the Genuine/Tampered 2 held-out split, but that split is generated.photos synthetic portraits — real-world passport/phone-camera validation is still required. The spectral heuristics remain as a corroborating signal, and the adapter falls back to them when torch/the checkpoint is missing.
- **Face calibration unvalidated** on real face data; grey-zone handling is conservative but the 0.75 mapping itself is a design choice, not an empirical ROC point.
- **Face-embedding reuse detection (DONE 2026-09-26).** Document-face SFace embeddings are now persisted per case (`face_embeddings` table + vector store) and cross-case FACE_REUSE fires in the anomaly stage above cosine 0.42. Bootstraps from the DB table on restart; the raw 128-d vector is stripped from stage JSON.
- **Dev-token endpoint** remains the auth story for demos; real deployments need OAuth2/OIDC and `AUTH_DEV_TOKEN_ENABLED=false`.
- Frontend dashboard exists (case detail with similarity bars, evidence, audit) but has no evidence *timeline* widget (Phase 12) — stage timestamps exist in DB, display is a UI task.

## 7. SIH Demo Flow (verified working)

UPLOAD DOCUMENT → OCR (+fields, name cross-check) → DOCUMENT VALIDATION (preprocessing) → FACE EXTRACTION/MATCH (YuNet+SFace, calibrated, uncertainty-aware) → LIVENESS (honest heuristic) → TAMPERING (ELA + regions) → CROSS-CASE ANALYSIS (hash/name/ID reuse) → RISK ENGINE (explainable contributions) → EXPLANATION (deterministic/Ollama) → OFFICER REVIEW (dashboard) → AUDIT ANCHOR (hash chain, verifiable).

## 8. Demo Test Cases

| Case | How to demo | Expected (verified) |
|---|---|---|
| Genuine | Upload doc, name matches OCR | name_cross_check=matched, low risk, chain valid |
| Identity reuse | Two cases, same ID number, different names | "repeated identity signal" anomaly, REVIEW_REQUIRED |
| Face mismatch | Selfie of different person (live capture) | face_mismatch rule, contribution with value/threshold |
| Tampered doc | ELA-sensitive edit (splice/paste) | tampering score↑, regions[] localized, signal strings |
| Uncertain/low-quality | Blank or noise image | face `match: None`, `uncertainty: no_face`, review forced |
| Model unavailable | No live capture for deepfake | stage `unavailable`, honest, no fake score |
| Concurrency | Double POST /screen | second call 409 with run id |
