# Data Strategy

## Core Research Datasets (non‑production)

| Dataset | Purpose | Notes |
|---|---|---|
| **MIDV‑500** | Document detection, perspective correction, OCR evaluation | Research‑only, licensing permits non‑commercial use. Use for benchmarking preprocessing and OCR pipelines. |
| **MIDV‑2019** | Harder document images, varied lighting and motion blur | Complementary to MIDV‑500 for robustness testing. |
| **PaddleOCR** | Primary OCR engine (fast, multi‑language) | Use as default OCR; Tesseract as fallback. |
| **Tesseract** | OCR fallback, open‑source | Useful for comparative evaluation. |
| **OpenCV** | Image preprocessing, quality analysis, document segmentation | Handles blur detection, rotation correction, cropping. |
| **DocTamper** | Document‑tampering detection research | Verify licensing before redistribution; may require model training. |
| **CelebA‑Spoof** | Anti‑spoof / liveness research | Large collection of spoofing attacks; non‑commercial use only. |
| **FaceForensics++** | Deep‑fake detection research | Provides manipulated face videos for model evaluation. |
| **OULU‑NPU** (optional) | Additional anti‑spoof benchmark | Use if further liveness evaluation is needed. |
| **InsightFace / ArcFace** | Face detection and embedding generation | Basis for face verification and similarity search. |
| **FAISS / pgvector** | Vector similarity / face reuse detection | Future component for fast nearest‑neighbor search. |
| **Redis** | Velocity / rate‑window support | Used for anomaly detection and rate limiting. |
| **Hyperledger Fabric** (future) | Permissioned blockchain audit integration | Not used in Phase 1, but design accommodates later anchoring. |

## Data Splits & Usage

- **Training data** – Reserved for model development (outside Phase 1). When training, use only the above research datasets and respect their licensing.
- **Validation data** – Sub‑set of the same datasets, kept separate from training to assess over‑fit.
- **Test data** – Hold‑out portion of each dataset; also create synthetic test cases to validate end‑to‑end pipeline.
- **Synthetic data** – Generated mock watchlists, MRZ strings, tampered document images, duplicated face embeddings, and audit‑chain events. Used for demos and CI tests; no real PII.

## Licensing & Restrictions

- Verify each dataset's license before redistribution or inclusion in a packaged release. Most are **research‑only** and prohibit commercial use.
- For any dataset requiring explicit permission (e.g., DocTamper, CelebA‑Spoof), store a copy locally under `data/raw/` and include a `README.md` documenting the license URL and any attribution requirements.
- Synthetic data is fully owned by the project and can be used in production demos.

## Data Management

- Store raw research datasets in `data/raw/` (git‑ignored). Processed forms and synthetic data go in `data/processed/` and `data/synthetic/` respectively.
- Never commit raw biometric images or real identity documents to the repository.
- Use environment variables to point to data directories; keep paths configurable.

---

*All dataset selections and licensing considerations are captured here for future phases. No actual dataset downloads occur in Phase 1.*
