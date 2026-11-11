# AI-Based Fake Identity & Document Screening System
### SIH 2026 — Problem Statement SIH26188 | Theme: Blockchain & Cybersecurity | Ministry of Home Affairs

> A multi-layer, explainable, privacy-aware screening platform that helps officers detect suspicious identity documents and forged biometrics through real AI/CV analysis — not mock responses.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Proposed Solution](#2-proposed-solution)
3. [Technical Approach](#3-technical-approach)
4. [System Architecture](#4-system-architecture)
5. [Feasibility](#5-feasibility)
6. [Viability](#6-viability)
7. [Impact & Benefits](#7-impact--benefits)
8. [Research / Data References](#8-research--data-references)
9. [Current Validation](#9-current-validation)
10. [How to Run](#10-how-to-run)
11. [API Reference](#11-api-reference)
12. [AI Pipeline — Honest Model Status](#12-ai-pipeline--honest-model-status)
13. [Known Limitations & Honest Gaps](#13-known-limitations--honest-gaps)
14. [Project Structure](#14-project-structure)
15. [Security Notes](#15-security-notes)

---

## 1. Problem Statement

### Challenge

Identity documents are increasingly exposed to forgery, manipulation, stolen identities and sophisticated digital attacks.

### Existing Gaps

| Gap | Impact |
|-----|--------|
| Manual document verification | Time-consuming, inconsistent |
| Fragmented verification checks | No unified view of evidence |
| Subtle tampering hard to detect | Easy for sophisticated forgeries to pass |
| Officers lack a unified evidence view | Decisions based on incomplete information |
| Audit trails difficult to verify | Poor accountability |

### Need

A multi-layer, explainable and privacy-aware screening system that assists officers in detecting suspicious identities and documents quickly.

---

## 2. Proposed Solution

**AI-Based Fake Identity & Document Screening System** — a unified screening platform that analyses identity documents through multiple independent verification layers.

### Core Modules

| Module | Technology |
|--------|-----------|
| Document preprocessing & quality analysis | OpenCV |
| OCR & field extraction | Tesseract 5.x + PaddleOCR fallback |
| Document and metadata validation | Rule-based field checks + regex |
| Tampering / forgery detection | ELA + high-frequency noise inconsistency |
| Face verification | YuNet (ONNX) + SFace (ONNX) deep embeddings |
| Liveness detection | Sharpness + entropy image metrics |
| Deepfake detection | FFT spectral analysis + chrominance dispersion |
| Cross-case anomaly detection | Content-hash + subject-name reuse across DB |
| Deterministic risk scoring | Evidence-weighted scoring engine |
| Explainable screening results | Deterministic templates + optional Ollama LLM |
| Tamper-evident audit trail | SHA-256 append-only hash-chain |

### Key Innovation

```
Multiple independent signals -> Evidence -> Explainable Risk -> Human Decision
```

---

## 3. Technical Approach

### Screening Pipeline

```
Upload
  -> File validation (type, size, MIME, path safety)
  -> PDF -> image rasterization (pdf2image) or direct OpenCV load
  -> Image quality analysis (blur, brightness, contrast)
  -> Document detection (contour-based)
  -> Perspective correction
  -> Rotation/deskew
  -> Image enhancement (CLAHE, denoising)
  -> OCR (Tesseract / PaddleOCR)
  -> Field extraction (Name, DOB, ID number, Gender)
  -> Name cross-check (applicant vs extracted)
  -> Tampering detection (ELA + noise analysis)
  -> Liveness detection (sharpness + entropy)
  -> Deepfake detection (FFT spectral + chrominance)
  -> Face verification (YuNet + SFace ONNX models)
  -> Anomaly detection (cross-case hash/name reuse)
  -> Deterministic risk engine (weighted evidence sum)
  -> Explanation generation (template + optional Ollama)
  -> Hash-chain audit record
  -> Officer Dashboard
```

---

## 4. System Architecture

```
CLIENT LAYER
  Applicant Portal              Officer Dashboard
  - Document Upload             - Case Queue
  - Selfie / Live Capture       - Findings Panel
  - Application Status          - Risk Assessment
                                - Evidence Panels
                                - Audit History

           |                           |
           v                           v

API & SECURITY LAYER (FastAPI)
  - JWT Authentication (dev scaffold -> OAuth2/OIDC production)
  - RBAC: officer / admin / auditor
  - Rate Limiting (per-user, Redis-backed when available)
  - Request & File Validation
  - Security Headers Middleware
  - CORS

           |

SCREENING ORCHESTRATOR
  - Case lifecycle management
  - Sequential stage invocation with evidence collection

           |

AI & FORENSICS ENGINE
  OCR          Tampering      Face         Liveness     Deepfake     Anomaly
  Tesseract    ELA + Noise    YuNet +      Sharp +      FFT +        Hash +
  PaddleOCR    Analysis       SFace        Entropy      Chroma       Name

           |

RISK ENGINE
  Evidence-weighted deterministic score (0-100)
  Levels: low / medium / high / REVIEW_REQUIRED

           |

OFFICER DASHBOARD
  Case Queue | Findings | Risk | Evidence | Audit History

DATA SERVICES
  SQLite / PostgreSQL  -- Cases, results, evidence
  Redis (optional)     -- Cache, rate-limit windows
  FAISS / memory store -- Vector similarity search

AUDIT LAYER
  Append-only SHA-256 Hash-Chain
  Future: Hyperledger Fabric anchor
```

**Security principle:** Raw PII and document images are never stored on any blockchain or shared log.
Only cryptographic hashes and required metadata are recorded in the audit chain.

---

## 5. Feasibility

### Technical Feasibility

- Built with mature open-source technologies (OpenCV, Tesseract, FastAPI, SQLAlchemy)
- Modular AI components — each adapter exposes a stable interface; mock <-> production swappable
- REST API enables integration with existing government systems
- Local deployment possible for air-gapped or sensitive environments
- Docker-ready architecture supports portability

### Operational Feasibility

- Automates repetitive first-level document checks
- Prioritizes cases requiring officer attention via risk scoring
- Provides structured evidence rather than black-box decisions
- Role-based access: officer, admin, auditor

### Scalability

- Stateless screening services
- Redis-based velocity caching (optional)
- SQLite for development; PostgreSQL for production
- FAISS or pgvector for similarity search
- Docker-ready architecture
- Future horizontal scaling with distributed workers

### Deployment Path

```
Prototype -> Controlled Pilot -> Scaled Deployment -> Government System Integration
```

---

## 6. Viability

| Dimension | Approach |
|-----------|----------|
| **Cost** | 100% open-source stack; no proprietary API dependencies |
| **Integration** | REST APIs compatible with existing identity workflows |
| **Maintainability** | Independent AI modules -- upgrade one without rebuilding system |
| **Security** | RBAC, field-level encryption hooks, audit logging, tamper-evident chain |
| **Long-Term Value** | Pluggable model architecture supports newer models and government databases |

---

## 7. Impact & Benefits

| Benefit | Description |
|---------|-------------|
| Faster Screening | Automates repetitive first-level document checks |
| Multi-Layer Detection | Combines document, biometric, forensic and behavioural signals |
| Explainable Results | Officers see exactly why a risk score was produced |
| Reduced Officer Workload | Prioritizes cases requiring deeper investigation |
| Stronger Security | Protects sensitive identity information and audit trail |
| Better Accountability | Every screening stage produces structured evidence and audit events |
| Human-in-the-Loop | AI assists; authorized officers make the final decision |

---

## 8. Research / Data References

### Datasets

| Dataset | Purpose |
|---------|---------|
| MIDV-500 | Document detection & OCR benchmarking |
| MIDV-2019 | Harder document-image conditions |
| CelebA-Spoof | Anti-spoofing research |
| FaceForensics++ | Deep-fake research |
| DocTamper | Document-tampering research |
| OULU-NPU | Optional anti-spoofing evaluation |
| Synthetic forged/manipulated document samples | Controlled testing |

### Technical References

- **OpenCV 5.0** -- Image processing, YuNet face detection, SFace recognition (ONNX)
- **Tesseract OCR 5.5.3** -- Primary OCR engine (confirmed installed)
- **PaddleOCR** -- Secondary OCR engine (optional install; auto-fallback)
- **FastAPI** -- ASGI web framework, async-capable
- **SQLAlchemy 2.x** -- ORM for PostgreSQL/SQLite
- **FAISS** -- Vector similarity search for face reuse detection
- **Redis** -- Velocity windows and caching
- **Docker** -- Containerization

### Government / Domain Reference

- UK Home Office guidance on fraudulent identity documents

---

## 9. Current Validation

### Prototype Status

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI backend | WORKING | Full API running on port 8000 |
| Authentication & RBAC | WORKING | JWT dev token + officer/admin/auditor roles |
| Case management | WORKING | Create, list, get cases via API |
| Document upload | WORKING | JPEG, PNG, TIFF (PDF via pdf2image if installed) |
| OpenCV preprocessing | WORKING | Quality, detection, perspective, rotation, enhancement |
| Tesseract OCR | WORKING | Tesseract 5.5.3 at C:\Program Files\Tesseract-OCR |
| Screening pipeline | WORKING | Full pipeline runs end-to-end in ~1-2s |
| Tampering detection | WORKING | ELA + noise inconsistency (real CV, not mocked) |
| Face verification | WORKING | YuNet + SFace ONNX models loaded, 128-dim embeddings |
| Liveness detection | WORKING | Sharpness + entropy signal analysis |
| Deepfake detection | WORKING | FFT spectral + chrominance dispersion analysis |
| Anomaly detection | WORKING | Content-hash + subject-name cross-case checks |
| Deterministic risk engine | WORKING | Evidence-weighted score 0-100 with level classification |
| Hash-chain audit layer | WORKING | SHA-256 append-only chain with integrity verify endpoint |
| Officer dashboard | WORKING | Real-time case table with risk levels, filters, case detail view |
| Applicant portal | WORKING | Document upload + selfie capture UI at /client/ |

### Automated Testing

```
20 tests PASSING (pytest)

tests/integration/test_screening_flow.py          1 test  -- full e2e pipeline
tests/unit/ai/test_deepfake.py                    3 tests -- deepfake adapter
tests/unit/ai/test_face_verification.py           3 tests -- face verification adapter
tests/unit/ai/test_liveness.py                    3 tests -- liveness adapter
tests/unit/ai/test_tampering.py                   3 tests -- tampering adapter
tests/unit/test_basic.py                          2 tests -- auth + protected routes
tests/unit/test_file_service_security.py          3 tests -- file service security
tests/unit/utils/test_redis_client.py             1 test  -- Redis client
tests/unit/vector/test_vector_store.py            1 test  -- vector store
```

### Verified End-to-End (live run)

Document with rendered name/DOB/ID number:
- OCR extracted: Name, DOB (15/08/2000), ID number (1234 5678 9012)
- Name cross-check: applicant matched document name at 100% score
- Tampering score: 0.384 (below 0.50 threshold -- not tampered)
- Face/liveness/deepfake: skipped (no live capture provided)
- Risk score: 7/100 (REVIEW_REQUIRED -- liveness/face skipped)
- Audit chain: all events recorded with SHA-256 hashes
- Pipeline time: ~1.1 seconds

---

## 10. How to Run

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Tested on 3.14.6 |
| Tesseract OCR | 5.x | https://github.com/UB-Mannheim/tesseract/wiki |
| pip packages | -- | See requirements.txt |

### Install Dependencies

```powershell
# From the project root: c:\Users\Ankush Arora\OneDrive\Desktop\SIH 2026
pip install -r requirements.txt
pip install python-dotenv pytesseract

# Optional: better OCR accuracy
pip install paddleocr paddlepaddle

# Optional: PDF support (also requires poppler for Windows)
pip install pdf2image
# Poppler: https://github.com/oschwartz10612/poppler-windows/releases
```

### Configure Environment

The `.env` file is pre-configured. Verify TESSERACT_CMD points to your install:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Start the Server

```powershell
cd "c:\Users\Ankush Arora\OneDrive\Desktop\SIH 2026"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Access the Application

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/ | Officer Dashboard |
| http://127.0.0.1:8000/client/ | Applicant Portal |
| http://127.0.0.1:8000/cases/{case_id} | Forensic Case Detail View |
| http://127.0.0.1:8000/docs | Interactive API documentation (Swagger UI) |
| http://127.0.0.1:8000/api/v1/health | Health check |

### Run Tests

```powershell
pytest
```

---

## 11. API Reference

Base URL: `http://127.0.0.1:8000/api/v1`

All endpoints except health and auth require `Authorization: Bearer <token>`.

### Authentication

```http
POST /auth/dev-token
Content-Type: application/json

{"user_id": "officer1", "role": "officer"}
```

Roles: `officer`, `admin`, `auditor`

### Cases

| Method | Endpoint | Roles | Description |
|--------|----------|-------|-------------|
| POST | /cases | officer, admin | Create a new case |
| GET | /cases | officer, admin, auditor | List all cases |
| GET | /cases/{case_id} | officer, admin, auditor | Get case details |

### Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /cases/{case_id}/files?file_type=document | Upload identity document |
| POST | /cases/{case_id}/files?file_type=live_capture | Upload selfie / live image |
| GET | /cases/{case_id}/files | List uploaded files |
| GET | /cases/{case_id}/files/{file_id}/content | Download file |

### Screening

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /cases/{case_id}/screen | Trigger full screening pipeline |
| GET | /cases/{case_id}/screening | Get latest screening results |

### Audit

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /cases/{case_id}/audit | List audit events |
| GET | /cases/{case_id}/audit/verify | Verify hash-chain integrity |

---

## 12. AI Pipeline -- Honest Model Status

### OCR -- Tesseract 5.5.3

| Item | Detail |
|------|--------|
| Engine | Tesseract 5.5.3 (system install confirmed) |
| Fallback | PaddleOCR (auto-fallback if not installed) |
| Preprocessing | Otsu binarization + Gaussian blur + 1.5x upscale for small images |
| Fields extracted | Name (heuristic), DOB (regex), ID number (regex), Gender (regex) |
| Tested | Confirmed working on synthetic and real Aadhaar images |

### Face Verification -- YuNet + SFace ONNX

| Item | Detail |
|------|--------|
| Detection | face_detection_yunet.onnx (OpenCV FaceDetectorYN) |
| Recognition | face_recognition_sface.onnx (OpenCV FaceRecognizerSF, 128-dim) |
| Method | Multi-scale + 4-orientation sweep, 5-landmark affine alignment, cosine similarity |
| Threshold | 0.363 (official SFace threshold), configurable via FACE_SIMILARITY_THRESHOLD |
| Status | Models loaded and verified. Requires document + live capture to produce a result |

### Document Tampering Detection

| Item | Detail |
|------|--------|
| Method | Error Level Analysis (ELA) + High-Frequency Noise Inconsistency |
| Algorithm | JPEG recompression at Q92, local block variance, noise residual grid analysis |
| Output | tampered: bool, score: float 0-1, regions: list, signals: list |
| Threshold | 0.50 (configurable via TAMPERING_SCORE_THRESHOLD) |
| Status | Pure OpenCV/NumPy -- no trained model required |

> NOTE: This is a forensic heuristic analyser. It detects JPEG compression anomalies and noise inconsistencies. It cannot detect high-quality printed forgeries or pixel-perfect edits. A trained model fine-tuned on DocTamper dataset is needed for production-grade forgery detection.

### Liveness Detection

| Item | Detail |
|------|--------|
| Method | Laplacian variance (sharpness) + histogram entropy |
| Thresholds | Sharpness >= 100.0, Entropy >= 5.0 (configurable via .env) |
| Limitation | No presentation-attack detection; a CelebA-Spoof trained model would be more robust |

### Deepfake Detection

| Item | Detail |
|------|--------|
| Method | 2D FFT power spectrum + Chrominance (YCrCb) noise dispersion |
| Input | Live capture image |
| Limitation | Spectral heuristics only; a FaceForensics++ trained classifier would be more robust |

### Risk Engine

| Item | Detail |
|------|--------|
| Method | Deterministic evidence-weighted sum |
| Weights | Tampering 25%, Deepfake 20%, Anomaly 15%, Liveness 15%, Face 15%, OCR 10% |
| Output | Risk score 0-100, levels: low / medium / high / REVIEW_REQUIRED |
| Status | Fully deterministic and reproducible |

---

## 13. Known Limitations & Honest Gaps

| Limitation | Impact | Mitigation Path |
|------------|--------|-----------------|
| No trained document forgery classifier | ELA catches compression anomalies only | Train/fine-tune on DocTamper dataset |
| No trained anti-spoof model | Uses image quality metrics, not PAD | Integrate CelebA-Spoof trained model |
| No trained deepfake classifier | Spectral heuristics, not neural classifier | Integrate FaceForensics++ trained model |
| PDF needs pdf2image + poppler | PDFs fail gracefully with install guidance | pip install pdf2image + poppler |
| PaddleOCR not installed | Falls back to Tesseract automatically | pip install paddleocr paddlepaddle |
| No MRZ parsing | Passport Machine Readable Zone not extracted | Integrate python-mrz or passporteye |
| No watchlist database | No real document/identity DB check | Connect to government identity databases |
| Face embeddings not stored | Cross-case face similarity not fully implemented | Integrate FAISS vector store |
| Dev JWT auth only | Not production-ready authentication | Replace with OAuth2/OIDC (Keycloak, etc.) |
| No TLS in dev | HTTP only | Configure nginx/uvicorn with SSL |
| datetime.utcnow() deprecation | Python 3.12+ warnings | Replace with datetime.now(datetime.UTC) |

---

## 14. Project Structure

```
SIH 2026/
+-- backend/
|   +-- ai/
|   |   +-- deepfake/          # FFT spectral deepfake detection
|   |   +-- face/              # YuNet + SFace ONNX face verification
|   |   |   +-- weights/       # face_detection_yunet.onnx, face_recognition_sface.onnx
|   |   +-- liveness/          # Sharpness + entropy liveness check
|   |   +-- ocr/               # Tesseract + PaddleOCR engines + service
|   |   +-- ollama/            # Explanation engine (LLM + deterministic fallback)
|   |   +-- tampering/         # ELA + noise inconsistency forensics
|   +-- api/                   # FastAPI route handlers
|   +-- blockchain/            # SHA-256 hash-chain audit ledger
|   +-- config.py              # Settings loaded from .env
|   +-- db/                    # SQLAlchemy models and session
|   +-- document/              # Image preprocessing (quality, detection, perspective, rotation)
|   +-- fraud/                 # Anomaly detector (cross-case checks)
|   +-- main.py                # FastAPI application entry point
|   +-- middleware/            # CORS, rate-limit, security headers
|   +-- models/                # Pydantic schemas
|   +-- pipeline/              # Pipeline contracts / status constants
|   +-- risk/                  # Deterministic risk engine
|   +-- security/              # Auth (JWT), RBAC
|   +-- services/              # Case, file, screening business logic
|   +-- utils/                 # Logging, Redis client
|   +-- vector/                # FAISS / memory vector store
+-- frontend/
|   +-- index.html             # Officer Dashboard (real-time SPA)
|   +-- client/
|       +-- index.html         # Applicant Portal (document + selfie upload)
+-- tests/
|   +-- integration/           # Full screening flow end-to-end test
|   +-- unit/                  # AI adapter + API + utility tests
+-- docker/                    # Docker configuration
+-- docker-compose.yml
+-- docs/                      # Architecture docs, API contracts, roadmap
+-- .env                       # Environment configuration (gitignored)
+-- .env.example               # Template for new installs
+-- pytest.ini
+-- requirements.txt
+-- README.md
```

---

## 15. Security Notes

- **File upload validation:** MIME type, extension whitelist, 10 MiB size limit, filename sanitization
- **No file execution:** Uploaded files are decoded only by OpenCV / Tesseract
- **Path traversal prevention:** All file paths resolved relative to UPLOAD_DIR
- **No PII in audit chain:** Only SHA-256 hashes and metadata in audit events
- **No hard-coded secrets:** All sensitive values read from .env
- **RBAC enforcement:** Every protected endpoint checks role before processing
- **Rate limiting:** Per-user request rate limit (Redis-backed when available)
- **Security headers:** X-Content-Type-Options, X-Frame-Options, etc. via middleware
- **Temporary files:** No temp files created; images processed in memory

---

## Credits

Built for **Smart India Hackathon 2026** -- SIH26188
Theme: Blockchain & Cybersecurity
Organization: Ministry of Home Affairs

Stack: Python 3.14 · FastAPI · OpenCV 5.0 · Tesseract 5.5.3 · SQLAlchemy 2.x · FAISS · Docker
