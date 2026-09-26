# Testing Strategy

A comprehensive testing plan ensures correctness, security, performance, and explainability of the screening system. Tests are organized by scope and layer.

---

## 1. Unit Tests

- Target: individual functions, utilities, and data‑validation logic.
- Framework: **pytest**.
- Coverage goal: ≥ 80 % for core modules (pipeline services, security helpers, DB models).
- Example: test OCR confidence aggregation, hash‑chain computation, role‑based permission decorator.

---

## 2. Integration Tests (API & Services)

- Spin up the FastAPI app with an in‑memory SQLite database.
- Tests cover full request/response cycles:
  - Case creation, file upload, screening trigger.
  - Verify that mock pipeline stages return deterministic results.
  - Ensure audit events are created and hash chain is valid.
- Use **httpx** test client for FastAPI.

---

## 3. API Contract Tests

- Validate that each endpoint conforms to the specifications in `docs/API_CONTRACTS.md`.
- Check status codes, required fields, error handling for malformed requests.
- Include negative tests for RBAC violations (e.g., AUDITOR trying to create a case).

---

## 4. Pipeline Stage Tests

- **Preprocessing** – feed synthetic images, assert quality_score range and output shape.
- **OCR** – use a small set of synthetic document images with known text; verify extracted fields and confidence values.
- **Tampering Detection** – provide clean vs tampered sample images; expect tamper_score thresholds.
- **Liveness** – mock live‑capture frames (static images) – expect deterministic pass/fail based on stage mock config.
- **Face Verification** – embed two identical synthetic faces; verify match true and similarity > threshold.
- **Anomaly Detection** – simulate repeated face embeddings across cases; assert appropriate flags.
- **Risk Scoring** – feed known stage outputs; verify final risk_score matches the weighted sum.
- **Explanation** – feed a risk result; verify the LLM‑generated summary contains expected reason strings (mocked).

---

## 5. Security Tests

- **Authentication** – invalid token rejection, token expiration handling.
- **Authorization** – ensure OFFICER cannot access another officer's case, AUDITOR read‑only, ADMIN full access.
- **Input Validation** – malformed JSON, oversized file uploads, disallowed MIME types.
- **Rate Limiting** – simulate rapid request bursts; expect 429 responses.
- **Encryption** – verify that encrypted fields cannot be read without the `ENCRYPTION_KEY`.

---

## 6. OCR Evaluation (Benchmark) – Phase 4 Preparation

- Use MIDV‑500 and MIDV‑2019 datasets for baseline OCR accuracy.
- Metrics: character error rate (CER), field‑level precision/recall.
- Record results in a benchmark report (future phase).

---

## 7. Tampering & Liveness Evaluation

- Run the heuristic tampering detector on DocTamper samples; compute detection rate.
- Run liveness detector on CelebA‑Spoof (spoof vs live) and report true‑positive/false‑negative rates.

---

## 8. Deterministic Risk Engine Tests

- Verify that given identical stage inputs, the risk score is reproducible.
- Test edge cases: all stages `failed` → risk_score = max (or defined failure handling).

---

## 9. Audit Integrity Tests

- Insert a series of mock events, then run the chain verification routine; assert `integrity_ok`.
- Corrupt a middle event’s `current_hash` and assert verification failure.

---

## 10. Performance Tests

- Load test the `/cases/{case_id}/screen` endpoint with parallel requests (simulating concurrent officer submissions).
- Measure latency per stage; ensure each stage stays under defined thresholds (e.g., OCR < 500 ms in mock mode).

---

## 11. End‑to‑End (E2E) Tests

- Scripted scenario reproducing the demo workflow (case creation → file upload → screening → risk view → audit verification).
- Validate UI interaction flow using a headless browser (e.g., Playwright) in later phases.

---

## 12. Adversarial / Negative Testing

- Feed malformed or malicious images (e.g., embedded script payload) to ensure the pipeline safely rejects them.
- Test with extremely large files to trigger size limits.
- Simulate repeated failed screening attempts to verify rate‑limit enforcement.

---

## 13. Continuous Integration

- All tests run on each commit via GitHub Actions.
- Linting with **ruff** (or flake8) and type checking with **mypy**.
- Coverage report generated; build fails if coverage drops below threshold.

---

*Phase 1 only includes the test plan and mock implementations; no real model or dataset files are downloaded. The tests act against deterministic mock adapters, ensuring repeatable results for the SIH demonstration.*
