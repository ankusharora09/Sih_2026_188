"""Screening service – orchestrates the multi-stage document/biometric screening pipeline.

A run is created synchronously (so the API can return the run id immediately)
and its stages execute asynchronously in a worker thread. Each stage commits
its ``StageResult`` row as soon as it completes, so a crash mid-pipeline
preserves all evidence gathered so far and the UI can poll live progress.
"""

from __future__ import annotations

import re
import threading
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from ..config import settings

# Module-level lock guarding run creation. SQLite has no atomic
# "insert where not exists", so two concurrent POST /screen requests could
# otherwise both pass the active-run check and start duplicate worker threads
# (the UI then flickers between two racing runs). Serializing creation closes
# the check-then-act race; the DB check below remains the source of truth.
_create_run_lock = threading.Lock()
from ..pipeline import contracts as plc
from ..fraud.anomaly_detector import AnomalyDetector
from ..db import models
from ..db.database import SessionLocal
from ..blockchain.hash_chain import record_audit
from ..ai.ollama.explanation_engine import ExplanationEngine
from ..risk.engine import RiskEngine
from ..ai.liveness import get_verifier as get_liveness_verifier
from ..ai.face import get_verifier as get_face_verifier
from ..ai.tampering import get_verifier as get_tamper_verifier
from ..ai.deepfake import get_verifier as get_deepfake_verifier

_VALID_STAGE_STATUSES = {plc.STATUS_SUCCESS, plc.STATUS_FAILED, plc.STATUS_UNAVAILABLE, plc.STATUS_SKIPPED}

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def _json_safe(value):
    """Convert numpy / nested values so SQLAlchemy JSON columns can persist them."""
    import math
    import numpy as np

    if value is None:
        return None
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _imread(path: str):
    """Load an image from disk, including Windows paths cv2.imread cannot open."""
    import numpy as np
    import cv2

    p = Path(path)
    if not p.is_file():
        return None
    data = np.fromfile(str(p), dtype=np.uint8)
    if data.size == 0:
        return None
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is not None:
        if img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        elif img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


def _pil_to_bgr(pil_img):
    """Convert a PIL RGB image to a numpy BGR image for OpenCV."""
    import numpy as np
    import cv2
    return cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)


def _load_screening_image(doc_file: models.DocumentFile):
    """Load the persisted upload as a numpy BGR image (PDF: first page via pdf2image)."""
    path = doc_file.stored_path
    if Path(path).suffix.lower() == ".pdf":
        try:
            from pdf2image import convert_from_path
        except ImportError:
            return None, ("PDF uploaded but 'pdf2image' is not installed. "
                          "Install it with: pip install pdf2image (also requires poppler). "
                          "Alternatively, upload a JPEG or PNG image.")
        try:
            pages = convert_from_path(path, dpi=200, first_page=1, last_page=1)
            return _pil_to_bgr(pages[0].convert("RGB")), None
        except Exception as exc:
            return None, f"PDF rasterization failed: {exc}"
    img = _imread(path)
    if img is None:
        return None, "Unable to decode uploaded document bytes"
    return img, None


# Identity-field extraction patterns (module level so they are compiled once).
_DOB_RE = re.compile(
    r'(?:DOB|Birth|D\.O\.B|Date of Birth)[:\s]+([0-9]{1,2}[/\-][0-9]{1,2}[/\-][0-9]{2,4})', re.I)
_DOB_HEADER_RE = re.compile(r'DOB|Date of Birth|Birth', re.I)
_AADHAAR_RE = re.compile(r'\b([0-9]{4}[ \t]+[0-9]{4}[ \t]+[0-9]{4})\b')  # single line only
_COMPACT_ID_RE = re.compile(r'(?<![0-9])([0-9]{12})(?![0-9])')
_PAN_RE = re.compile(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b')
_GENDER_RE = re.compile(r'\b(Male|Female|Transgender)\b', re.I)
# Lines that look like document boilerplate, never like a person's name.
_NOT_NAME_RE = re.compile(
    r'\b(government|india|unique|authority|aadhaar|male|female|proof|identity|citizenship'
    r'|birth|verification|online|offline|signature|download|helpdesk|enrollment)\b', re.I)


def extract_identity_fields(raw_text: str, subject_name: str | None = None) -> dict:
    """Extract DOB / ID number / gender / name from OCR text and cross-check the name.

    The name cross-check compares the case's ``subject_name`` against both the
    extracted document name and the full OCR text (token overlap, best wins).
    """
    dob_m = _DOB_RE.search(raw_text)
    id_m = (_AADHAAR_RE.search(raw_text)
            or _COMPACT_ID_RE.search(raw_text)
            or _PAN_RE.search(raw_text))
    gender_m = _GENDER_RE.search(raw_text)

    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    extracted_name = _extract_document_name(lines)

    subj = (subject_name or "").strip()
    name_verif = {
        "applicant_name": subj or None,
        "extracted_name": extracted_name,
        "match": None,
        "status": "not_provided" if not subj else "unmatched",
        "match_score": 0.0,
        "message": "Applicant name not provided" if not subj else "Name not verified",
    }
    if subj:
        app_tokens = set(re.sub(r'[^a-zA-Z\s]', '', subj).lower().split())
        if app_tokens:
            ext_tokens = set(re.sub(r'[^a-zA-Z\s]', '', extracted_name or '').lower().split())
            text_tokens = set(re.sub(r'[^a-zA-Z\s]', '', raw_text).lower().split())
            score = max(
                len(app_tokens & ext_tokens) / len(app_tokens) if ext_tokens else 0.0,
                len(app_tokens & text_tokens) / len(app_tokens),
            )
            if score >= 0.70:
                name_verif.update(match=True, status="matched", match_score=round(score, 2),
                                  message=f"Verified: Applicant '{subj}' matches document '{extracted_name or subj}'")
            elif score >= 0.40:
                name_verif.update(match=True, status="partial_match", match_score=round(score, 2),
                                  message=f"Partial Match: Applicant '{subj}' partially matches document '{extracted_name or 'text'}'")
            else:
                name_verif.update(match=False, status="mismatched", match_score=round(score, 2),
                                  message=f"Mismatch Alert: Applicant '{subj}' does NOT match document name '{extracted_name or 'Not Found'}'")

    return {
        "extracted_name": extracted_name,
        "extracted_dob": dob_m.group(1) if dob_m else None,
        "extracted_id_number": id_m.group(1) if id_m else None,
        "extracted_gender": gender_m.group(1) if gender_m else None,
        "name_cross_check": name_verif["status"],
        "name_verification": name_verif,
    }


def _extract_document_name(lines: list[str]) -> str | None:
    """Heuristic name extraction: the line above DOB, else a 2-4 word line."""
    for idx, line in enumerate(lines):
        if _DOB_HEADER_RE.search(line) and idx > 0:
            cleaned = re.sub(r'[^A-Za-z\s]', '', lines[idx - 1]).strip()
            if len(cleaned) >= 3 and not _NOT_NAME_RE.search(cleaned):
                return cleaned
    for line in lines:
        cleaned = re.sub(r'[^A-Za-z\s]', '', line).strip()
        words = cleaned.split()
        if 2 <= len(words) <= 4 and all(len(w) >= 2 for w in words) and not _NOT_NAME_RE.search(cleaned):
            return cleaned
    return None


def serialize_run(run: models.ScreeningRun) -> dict:
    return {
        "id": run.id,
        "screening_run_id": run.id,
        "case_id": run.case_id,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "stage_results": [{
            "stage": sr.stage,
            "status": sr.status,
            "confidence": sr.confidence,
            "result": sr.result,
            "metadata": sr.meta,
            "errors": sr.errors,
            "processing_time_ms": sr.processing_time_ms,
        } for sr in run.stage_results],
        "source_file_id": getattr(run, "source_file_id", None),
    }


# ---------------------------------------------------------------------------
# Run creation / job management
# ---------------------------------------------------------------------------

def create_screening_run(db: Session, case_id: str, actor_id: str | None = None) -> models.ScreeningRun:
    """Create a screening run row and enqueue the pipeline in the background.

    Returns immediately with the run in ``queued`` status; stages appear
    incrementally via ``GET /cases/{id}/screening`` as the worker completes
    them. Raises ``ValueError`` if the case already has a queued/running run.
    """
    try:
        with _create_run_lock:
            existing = (
                db.query(models.ScreeningRun)
                .filter(models.ScreeningRun.case_id == case_id,
                        models.ScreeningRun.status.in_(["queued", "running"]))
                .first()
            )
            if existing:
                return existing

            case_row = db.query(models.Case).filter(models.Case.id == case_id).first()
            if not case_row:
                raise ValueError(f"Case {case_id} not found")

            run = models.ScreeningRun(id=str(uuid4()), case_id=case_id, status="queued",
                                      started_at=datetime.utcnow())
            db.add(run)
            case_row.status = "screening"
            db.commit()
    except Exception:
        db.rollback()
        raise

    thread = threading.Thread(target=_execute_run, args=(run.id, case_id, actor_id or "system"),
                              daemon=True, name=f"screening-{run.id[:8]}")
    thread.start()
    db.refresh(run)
    return run


def _execute_run(run_id: str, case_id: str, actor_id: str) -> None:
    """Worker-thread body: run every stage on its own DB session.

    Exactly one worker executes a run_id; a second invocation for the same id
    (defensive idempotency) is ignored.
    """
    db = SessionLocal()
    try:
        run = db.query(models.ScreeningRun).filter(models.ScreeningRun.id == run_id).first()
        case_row = db.query(models.Case).filter(models.Case.id == case_id).first()
        if not run or not case_row:
            return
        if run.status not in ("queued", None):
            # Another worker already owns this run — never execute twice.
            return
        run.status = "running"
        case_row.status = "screening"
        db.commit()

        doc_file = _latest_document(db, case_id)
        if doc_file is None:
            _fail_run(db, run, case_row, "preprocessing", "No document uploaded for this case")
            return

        ctx = RunContext(run=run, case_id=case_id, actor_id=actor_id, doc_file=doc_file, db=db)
        ctx.stage("preprocessing", lambda: _stage_preprocessing(ctx))
        ctx.stage("ocr", lambda: _stage_ocr(ctx))
        ctx.stage("tampering_detection", lambda: _stage_tampering(ctx))
        ctx.stage("liveness_detection", lambda: _stage_liveness(ctx))
        ctx.stage("face_verification", lambda: _stage_face(ctx))
        ctx.stage("deepfake_detection", lambda: _stage_deepfake(ctx))
        ctx.stage("anomaly_detection", lambda: _stage_anomaly(ctx))
        ctx.stage("risk_engine", lambda: _stage_risk(ctx))
        ctx.stage("explanation", lambda: _stage_explanation(ctx))
        _finalize_run(db, ctx)
    except Exception as exc:  # never let the worker thread die silently
        try:
            run = db.query(models.ScreeningRun).filter(models.ScreeningRun.id == run_id).first()
            case_row = db.query(models.Case).filter(models.Case.id == case_id).first()
            if run and case_row:
                _fail_run(db, run, case_row, "pipeline", f"Unexpected pipeline error: {exc}")
        except Exception:
            pass
    finally:
        db.close()


def _latest_document(db: Session, case_id: str) -> models.DocumentFile | None:
    """Latest uploaded document for THIS case only (never another case's file)."""
    for file_type in ("document", None):
        doc = (
            db.query(models.DocumentFile)
            .filter(models.DocumentFile.case_id == case_id,
                    *([models.DocumentFile.file_type == file_type] if file_type else []))
            .order_by(models.DocumentFile.uploaded_at.desc())
            .first()
        )
        if doc:
            return doc
    return None


def _fail_run(db: Session, run: models.ScreeningRun, case_row: models.Case,
              stage: str, error: str) -> None:
    db.add(models.StageResult(id=str(uuid4()), run_id=run.id, stage=stage,
                              status=plc.STATUS_FAILED, errors=error))
    run.status = "failed"
    run.completed_at = datetime.utcnow()
    case_row.status = "failed"
    db.commit()


def _finalize_run(db: Session, ctx: RunContext) -> None:
    """Set the run and case final statuses once every stage has run."""
    pre_status = (ctx.db.query(models.StageResult)
                  .filter(models.StageResult.run_id == ctx.run.id,
                          models.StageResult.stage == "preprocessing")
                  .first())
    completed_ok = bool(pre_status and pre_status.status == plc.STATUS_SUCCESS)
    ctx.run.status = "completed" if completed_ok else "failed"
    ctx.run.completed_at = datetime.utcnow()
    case_row = db.query(models.Case).filter(models.Case.id == ctx.case_id).first()
    if case_row:
        risk = ctx.stage_results.get("risk_engine", {})
        decision = str(risk.get("decision_status") or "").upper()
        review = risk.get("review_required") or decision in ("REVIEW_REQUIRED", "REVIEW")
        case_row.status = ("failed" if not completed_ok
                           else "review_required" if review
                           else "completed")
    db.commit()


class RunContext:
    """Carries per-run state and persists one StageResult per completed stage."""

    def __init__(self, run: models.ScreeningRun, case_id: str, actor_id: str,
                 doc_file: models.DocumentFile, db: Session):
        self.run = run
        self.case_id = case_id
        self.actor_id = actor_id
        self.doc_file = doc_file
        self.db = db
        self.img = None
        self.enhanced_img = None
        self.live_img = None
        self.ocr_result: dict = {}
        self.ocr_status: str = plc.STATUS_SKIPPED
        self.name_verif: dict = {"status": "not_available"}
        self.face_reuse: dict | None = None
        self.stage_results: dict = {}
        self.risk_result: dict = {}

    # -- persistence -------------------------------------------------------

    def stage(self, stage_name: str, fn) -> dict:
        """Run one stage, persist its StageResult + audit event, commit.

        An exception inside a stage is recorded as that stage's failure and
        does not abort the remaining stages.
        """
        start = time.perf_counter()
        try:
            result, status = fn()
        except Exception as exc:
            result, status = {"error": f"{stage_name} raised: {exc}"}, plc.STATUS_FAILED
        # A stage that never executed has no honest duration — persist null
        # (rendered as NOT RUN) instead of a misleading ~0ms figure.
        elapsed_ms = (int((time.perf_counter() - start) * 1000)
                      if status not in (plc.STATUS_SKIPPED, plc.STATUS_UNAVAILABLE) else None)
        self.db.add(models.StageResult(
            id=str(uuid4()),
            run_id=self.run.id,
            stage=stage_name,
            status=status,
            result=_json_safe(result),
            processing_time_ms=elapsed_ms,
        ))
        record_audit(self.db, self.actor_id, f"{stage_name}_completed",
                     case_id=self.case_id, screening_run_id=self.run.id, meta={"status": status})
        self.db.commit()
        self.stage_results[stage_name] = result
        return result


# ---------------------------------------------------------------------------
# Stages (pure-ish: return (result_dict, status), mutations via ctx)
# ---------------------------------------------------------------------------

def _stage_preprocessing(ctx: RunContext):
    from ..document import quality, document_detector, perspective, rotation, enhancement

    img, load_error = _load_screening_image(ctx.doc_file)
    if img is None:
        return {"file_id": ctx.doc_file.id, "filename": ctx.doc_file.filename,
                "error": load_error or "Unable to read uploaded document"}, plc.STATUS_FAILED

    result = {
        "file_id": ctx.doc_file.id,
        "filename": ctx.doc_file.filename,
        "quality": quality.analyze_quality(img),
        "enhancement_applied": True,
    }
    status = plc.STATUS_SUCCESS

    detection = document_detector.detect_document(img)
    result["detection"] = detection
    if detection["status"] == "success":
        perspective_out = perspective.correct_perspective(img, detection["contour"])
        if perspective_out["status"] == "success":
            img = perspective_out["corrected_image"]
            result["perspective"] = perspective_out["metadata"]
        else:
            status = plc.STATUS_FAILED
        rotation_out = rotation.detect_and_correct_rotation(img, detection["contour"])
        if rotation_out["status"] == "success":
            img = rotation_out["rotated_image"]
            result["rotation"] = {"metadata": rotation_out["metadata"]}
        else:
            status = plc.STATUS_FAILED

    ctx.img = img
    ctx.enhanced_img = enhancement.enhance_image(img)
    return result, status


def _stage_ocr(ctx: RunContext):
    from ..ai.ocr import service as ocr_service
    from .document_validation import validate_document

    if ctx.img is None:  # preprocessing failed
        return {}, plc.STATUS_SKIPPED
    try:
        ocr_out = ocr_service.perform_ocr(ctx.img)
        if not ocr_out.get("result", {}).get("raw_text") and ctx.enhanced_img is not None:
            alt_out = ocr_service.perform_ocr(ctx.enhanced_img)
            if alt_out.get("result", {}).get("raw_text"):
                ocr_out = alt_out

        if ocr_out.get("status") == "unavailable":
            ctx.ocr_status = plc.STATUS_UNAVAILABLE
            return ocr_out.get("result", {}), plc.STATUS_UNAVAILABLE

        ocr_result = ocr_out["result"]
        case_row = ctx.db.query(models.Case).filter(models.Case.id == ctx.case_id).first()
        ocr_result["fields"] = extract_identity_fields(
            ocr_result.get("raw_text", ""), case_row.subject_name if case_row else None)
        # SIH Module 2: document-type detection, type-specific fields, rule validation
        try:
            ocr_result["validation"] = validate_document(ocr_result.get("raw_text", ""))
        except Exception as val_exc:
            ocr_result["validation"] = {"status": "failed", "error": str(val_exc)}
        ctx.ocr_result = ocr_result
        ctx.ocr_status = plc.STATUS_SUCCESS
        ctx.name_verif = ocr_result["fields"]["name_verification"]
        return ocr_result, plc.STATUS_SUCCESS
    except Exception as ocr_exc:
        ctx.ocr_status = plc.STATUS_FAILED
        return {"error": f"OCR raised an exception: {ocr_exc}"}, plc.STATUS_FAILED


def _stage_liveness(ctx: RunContext):
    live_file = (
        ctx.db.query(models.DocumentFile)
        .filter(models.DocumentFile.case_id == ctx.case_id,
                models.DocumentFile.file_type == "live_capture")
        .order_by(models.DocumentFile.uploaded_at.desc())
        .first()
    )
    if live_file is None:
        return {"status": "skipped", "reason": "live capture was not provided"}, plc.STATUS_SKIPPED

    live_img = _imread(live_file.stored_path)
    if live_img is None:
        return {"status": "failed", "error": "Unable to read live capture image", "is_live": False}, plc.STATUS_FAILED
    ctx.live_img = live_img
    result = get_liveness_verifier().detect(live_img)
    status = plc.STATUS_SUCCESS if result.get("status") == "success" else plc.STATUS_FAILED
    return result, status


def _stage_tampering(ctx: RunContext):
    if ctx.enhanced_img is None:
        return {}, plc.STATUS_SKIPPED
    result = get_tamper_verifier().detect(ctx.enhanced_img)
    # SIH Module 3: metadata / EXIF forensics from the ORIGINAL upload bytes
    try:
        from ..ai.tampering.metadata_analysis import analyze_metadata
        from PIL import Image as _PILImage
        meta: dict = {"status": "skipped"}
        try:
            with _PILImage.open(ctx.doc_file.stored_path) as orig:
                meta = analyze_metadata(orig, source_path=ctx.doc_file.stored_path)
        except Exception:
            meta = {"status": "unavailable", "note": "original file could not be opened for metadata analysis"}
        result["metadata"] = meta
        if meta.get("status") == "success":
            result.setdefault("signals", []).extend(
                f"metadata_{meta.get('risk_level', 'info')}: {s}" for s in meta.get("signals", [])[:3])
    except Exception as meta_exc:
        result["metadata"] = {"status": "failed", "error": str(meta_exc)}
    status = plc.STATUS_SUCCESS if result.get("status") == "success" else plc.STATUS_FAILED
    return result, status


def _stage_face(ctx: RunContext):
    if ctx.img is None or ctx.live_img is None:
        return {"status": "skipped", "reason": "live capture was not provided",
                "face_detected": False, "similarity": None, "match": None}, plc.STATUS_SKIPPED
    verifier = get_face_verifier()
    face_result = verifier.verify(ctx.img, ctx.live_img)
    if not face_result.get("face_detected") and ctx.enhanced_img is not None:
        alt_face = verifier.verify(ctx.enhanced_img, ctx.live_img)
        if alt_face.get("face_detected"):
            face_result = alt_face
    status = face_result.get("status") or plc.STATUS_FAILED
    if status not in _VALID_STAGE_STATUSES:
        status = plc.STATUS_FAILED
    # Phase 5E: persist the document-face embedding and detect cross-case
    # face reuse via the vector store. The raw 128-d vector is stripped from
    # the persisted stage result; only the reuse signal is surfaced.
    try:
        from ..fraud.face_reuse import persist_face_embedding

        persistence = persist_face_embedding(ctx.db, ctx.case_id, face_result)
        ctx.face_reuse = (persistence or {}).get("reuse")
        face_result["face_reuse_check"] = {
            "status": (persistence or {}).get("status", "skipped"),
            "similarity_to_prior": (persistence or {}).get("similarity_to_prior"),
        }
        face_result.pop("document_embedding", None)
    except Exception:
        face_result.pop("document_embedding", None)
    return face_result, status


def _stage_deepfake(ctx: RunContext):
    if ctx.enhanced_img is None:
        return {}, plc.STATUS_SKIPPED
    if ctx.live_img is None:
        return {"status": "skipped", "reason": "live capture was not provided"}, plc.STATUS_SKIPPED
    result = get_deepfake_verifier().detect(ctx.enhanced_img, ctx.live_img)
    status = result.get("status") or plc.STATUS_FAILED
    if status not in _VALID_STAGE_STATUSES:
        status = plc.STATUS_FAILED
    return result, status


def _stage_anomaly(ctx: RunContext):
    result = AnomalyDetector(ctx.db).detect_for_case(ctx.case_id)
    status = plc.STATUS_SUCCESS if result.get("status") == "success" else plc.STATUS_FAILED
    # Merge the cross-case FACE_REUSE signal from the vector store (Phase 5E).
    if ctx.face_reuse:
        result.setdefault("anomalies", []).append(
            f"Face reuse: same face embedding detected in case {ctx.face_reuse.get('related_case_id', '?')} "
            f"(cosine {ctx.face_reuse.get('cosine_similarity')})")
        result.setdefault("signals", []).append(ctx.face_reuse)
        result["score"] = min(1.0, float(result.get("score") or 0.0) + 0.35)
        result["face_reuse"] = ctx.face_reuse
    return result, status


def _stage_risk(ctx: RunContext):
    ocr_conf = ctx.ocr_result.get("confidence") if isinstance(ctx.ocr_result, dict) else None
    stage_results_dict = {
        "tampering": ctx.stage_results.get("tampering_detection", {}),
        "liveness": ctx.stage_results.get("liveness_detection", {}),
        "deepfake": ctx.stage_results.get("deepfake_detection", {}),
        "face_mismatch": ctx.stage_results.get("face_verification", {}),
        "ocr_confidence": {
            "status": ctx.ocr_status if ctx.ocr_status == plc.STATUS_SUCCESS else (ctx.ocr_status or "skipped"),
            "confidence": ocr_conf,
        },
        "anomaly": ctx.stage_results.get("anomaly_detection", {}),
        "document_validation": {
            "status": ctx.ocr_status if ctx.ocr_status == plc.STATUS_SUCCESS else "skipped",
            "validation": (ctx.ocr_result or {}).get("validation", {}),
        },
    }
    risk_result = RiskEngine().compute(stage_results_dict)

    if ctx.name_verif.get("status") == "mismatched":
        risk_result.setdefault("triggered_rules", []).append("name_mismatch")
        risk_result["review_required"] = True
        risk_result["name_verification"] = ctx.name_verif
        risk_result["decision_status"] = "REVIEW_REQUIRED"
    ctx.risk_result = risk_result
    return risk_result, plc.STATUS_SUCCESS


def _stage_explanation(ctx: RunContext):
    text = ExplanationEngine().generate(ctx.risk_result)
    status_key = ctx.name_verif.get("status")
    if status_key == "mismatched":
        text += (f"\n- [ALERT] IDENTITY NAME MISMATCH: Applicant '{ctx.name_verif.get('applicant_name')}' "
                 f"does not match document name '{ctx.name_verif.get('extracted_name')}'.")
    elif status_key == "matched":
        text += (f"\n- [VERIFIED] IDENTITY NAME MATCHED: Applicant '{ctx.name_verif.get('applicant_name')}' "
                 f"matches document name '{ctx.name_verif.get('extracted_name')}'.")
    return {"explanation": text}, plc.STATUS_SUCCESS


def get_screening_run(db: Session, run_id: str) -> models.ScreeningRun | None:
    return db.query(models.ScreeningRun).filter(models.ScreeningRun.id == run_id).first()
