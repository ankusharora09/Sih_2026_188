"""Persist face embeddings and detect cross-case face reuse (Phase 5E).

At the end of a screening run the document-face SFace embedding is stored in
the ``face_embeddings`` table and mirrored into the configured vector store.
The next case with a similar face (cosine >= threshold, from a *different*
case) yields a FACE_REUSE signal — the strongest coordinated-fraud signal in
the architecture, previously listed as unimplemented.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..db import models
from ..vector import get_vector_store

# SFace cosine threshold for reuse: a bit above the official 0.363 match gate
# so only confident duplicates fire the cross-case signal. Configurable via
# FACE_REUSE_COSINE_THRESHOLD in .env.
_FACE_REUSE_COSINE_THRESHOLD = float(
    getattr(settings, "FACE_REUSE_COSINE_THRESHOLD", 0.42))


def _round_vector(vec) -> list[float]:
    return [round(float(x), 5) for x in vec]


# The vector-store factory returns a new instance per call; face reuse needs
# one shared, persistent index. Keep a module-level singleton and bootstrap it
# from the face_embeddings table so an in-memory backend survives restarts.
_store = None
_store_bootstrapped = False


def _get_store():
    global _store
    if _store is None:
        _store = get_vector_store()
    return _store


def _bootstrap_store(db: Session) -> None:
    """Load previously persisted embeddings into the store (idempotent)."""
    global _store_bootstrapped
    if _store_bootstrapped:
        return
    _store_bootstrapped = True
    try:
        for row in db.query(models.FaceEmbedding).all():
            _get_store().add(row.vector_id, row.embedding)
    except Exception:
        pass


def _reset_store_for_tests() -> None:
    """Drop the singleton index (test isolation; not used in production)."""
    global _store, _store_bootstrapped
    _store = None
    _store_bootstrapped = False


def _case_label(db: Session, case_id: str) -> str:
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    return case.subject_name or "unknown subject" if case else "unknown subject"


def persist_face_embedding(db: Session, case_id: str, face_result: dict) -> dict:
    """Store this case's document-face embedding and search for reuse.

    ``face_result`` is the face_verification stage result; it must carry
    ``face_detected: True`` and a raw SFace cosine ``raw_cosine`` for a match
    pair, from which we reconstruct the normalized embedding via
    ``HaarFaceVerificationAdapter._embed`` on the aligned crops. For
    simplicity and stability we re-embed from the aligned crop cached on the
    stage result when available; otherwise we skip persistence silently.

    Returns a dict describing what happened (for the stage metadata):
    - ``status``: "stored" | "skipped" | "failed"
    - ``reuse``: reuse info dict when a similar prior case exists
    """
    embedding = (face_result or {}).get("document_embedding")
    if not embedding:
        return {"status": "skipped", "reason": "no document embedding in face result"}

    try:
        vec = _round_vector(embedding)
        if len(vec) != 128:
            return {"status": "skipped", "reason": f"unexpected embedding dim {len(vec)}"}

        _bootstrap_store(db)
        store = _get_store()
        vector_id = f"case:{case_id}"
        store.add(vector_id, vec)  # idempotent: one row per case

        hits = [h for h in store.query(vec, top_k=5) if h[0] != vector_id]
        best_id, best_sim = (hits[0] if hits else (None, None))

        prior_case_id = None
        if best_id and best_id.startswith("case:"):
            prior_case_id = best_id.split(":", 1)[1]
        # Only count hits that map to a real prior case row.
        if prior_case_id:
            exists = db.query(models.Case).filter(models.Case.id == prior_case_id).first()
            if not exists:
                prior_case_id, best_sim = None, None

        cosine = None
        if best_sim is not None:
            cosine = float(best_sim)

        row = models.FaceEmbedding(
            case_id=case_id,
            vector_id=vector_id,
            embedding=vec,
            model_name=str((face_result or {}).get("model") or "sface_deep_onnx"),
            model_version=str((face_result or {}).get("model_version") or "unknown"),
            similarity_to_prior=cosine,
            matched_case_id=prior_case_id if (cosine or 0) >= _FACE_REUSE_COSINE_THRESHOLD else None,
        )
        db.add(row)
        db.commit()

        reuse = None
        if prior_case_id and cosine is not None and cosine >= _FACE_REUSE_COSINE_THRESHOLD:
            reuse = {
                "type": "face_reuse",
                "severity": "high",
                "related_case_id": prior_case_id,
                "cosine_similarity": round(cosine, 4),
                "threshold": _FACE_REUSE_COSINE_THRESHOLD,
                "model": (face_result or {}).get("model") or "sface_deep_onnx",
                "signal": "repeated face signal across cases",
            }
        return {"status": "stored", "reuse": reuse,
                "similarity_to_prior": round(cosine, 4) if cosine is not None else None}
    except Exception as exc:
        db.rollback()
        return {"status": "failed", "error": str(exc)}


def detect_face_reuse(db: Session, case_id: str) -> dict:
    """Post-hoc face-reuse lookup for ``case_id`` from persisted embeddings."""
    row = (
        db.query(models.FaceEmbedding)
        .filter(models.FaceEmbedding.case_id == case_id)
        .order_by(models.FaceEmbedding.created_at.desc())
        .first()
    )
    if not row or row.similarity_to_prior is None:
        return {"status": "success", "face_reuse": None}
    reuse = None
    if row.matched_case_id and row.similarity_to_prior >= _FACE_REUSE_COSINE_THRESHOLD:
        reuse = {
            "type": "face_reuse",
            "severity": "high",
            "related_case_id": row.matched_case_id,
            "cosine_similarity": round(float(row.similarity_to_prior), 4),
            "threshold": _FACE_REUSE_COSINE_THRESHOLD,
            "signal": "repeated face signal across cases",
        }
    return {"status": "success", "face_reuse": reuse}
