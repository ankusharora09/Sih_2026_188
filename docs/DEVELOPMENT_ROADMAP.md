# Development Roadmap

The project is split into **five** sequential development phases. Each phase builds on the artifacts created in the previous one and adds concrete implementation work. Phase 1 (current) is limited to architecture, specifications, and documentation.

---

## Phase 1 – Architecture, Specification & Data Strategy (Current)

- Audit the existing repository.
- Consolidate architecture in **`ARCHITECTURE_README.md`** (primary source of truth).
- Define module boundaries, service responsibilities, and data flow.
- Produce detailed contract documents:
  - `docs/API_CONTRACTS.md`
  - `docs/PIPELINE_CONTRACTS.md`
  - `docs/DATABASE_DESIGN.md`
  - `docs/SECURITY_ARCHITECTURE.md`
  - `docs/AUDIT_BLOCKCHAIN.md`
  - `docs/DATA_STRATEGY.md`
  - `docs/TESTING_STRATEGY.md`
  - `docs/DEVELOPMENT_ROADMAP.md`
  - `docs/DATASET_NOTES.md`
- Create repository scaffolding (`docs/` folder, `.env.example`, `.gitignore`).
- No code implementation, no model or dataset downloads.

**Deliverables:** All documentation files listed above, repository structure, and a clean git commit labeling Phase 1 completion.

---

## Phase 2 – Backend Foundation (APIs, DB, Auth, Contracts)

- Initialize a **FastAPI** project under `backend/`.
- Implement the API contracts defined in Phase 1.
- Set up PostgreSQL (or SQLite for early dev) connection via SQLAlchemy.
- Add JWT dev‑token endpoint and scaffold OAuth2/OIDC placeholders.
- Implement RBAC middleware using the role model.
- Create database migrations for the entities defined in `docs/DATABASE_DESIGN.md`.
- Health check endpoint.
- Write unit and integration tests for the API.

**Exit criteria:**
- `POST /cases` returns a `case_id`.
- `GET /health` returns `{"status":"ok"}`.
- Basic auth and RBAC work.

---

## Phase 3 – Full Mock Screening Pipeline

- Implement deterministic mock services for each pipeline stage (preprocessing, OCR, tampering, liveness, face verification, anomaly detection, risk scoring, explanation, audit).
- Orchestrator calls services in parallel where appropriate and stores mock results.
- Extend API with screening endpoints (`POST /cases/{case_id}/screen`).
- Populate audit chain entries for each stage.
- Add end‑to‑end tests that exercise the full pipeline.

**Exit criteria:**
- A case can be screened from start to finish with reproducible mock results.
- Risk score and audit chain are returned.

---

## Phase 4 – Real Preprocessing + OCR Integration

- Replace mock preprocessing with OpenCV‑based quality checks and perspective correction.
- Integrate PaddleOCR (primary) with Tesseract fallback.
- Add optional MRZ parsing.
- Verify OCR accuracy against MIDV‑500/MIDV‑2019 benchmark datasets (record metrics).
- Update API to expose raw OCR output for debugging.

**Exit criteria:**
- OCR accuracy meets a defined threshold (e.g., > 90 % field‑level F1).
- Preprocessing improves image quality scores.

---

## Phase 5 – Real AI, Security Hardening & Blockchain Integration

- Swap mock tampering, liveness, deep‑fake, and face verification services with production‑grade models trained on the research datasets.
- Harden security: TLS, rate limiting, secret management, full encryption at rest, OAuth2/OIDC.
- Implement Hyperledger Fabric adapter to anchor audit hashes on a permissioned ledger.
- Conduct performance, load, and security testing at scale.
- Finalize documentation, CI/CD pipelines, Docker containers, and deployment scripts.

**Exit criteria:**
- All stages run with real models, passing defined accuracy metrics.
- Audit chain can be verified locally and on‑chain.
- System passes security audit checklist.
- Demo ready for SIH presentation with realistic synthetic data.

---

## Ongoing Conventions (applies to all phases)

- **Python 3.11+**, type hints, modular services.
- No hard‑coded secrets or absolute Windows paths.
- Environment‑based configuration (`.env.example`).
- Clear, consistent naming, minimal dependencies.
- All AI modules are replaceable via the contracts defined in `docs/PIPELINE_CONTRACTS.md`.

---

*Phase 1 is now complete. The next actionable step is to begin Phase 2 implementation, starting with the FastAPI skeleton and database setup.*
