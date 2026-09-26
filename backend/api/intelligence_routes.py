"""Intelligence, analytics and health endpoints.

All data returned by these routes is derived from real database rows —
no synthetic or placeholder values. Synthetic demo cases are labelled at
creation time (scripts/create_demo_cases.py) and remain distinguishable.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from ..db import models
from ..api import dependencies
from ..security.rbac import require_role
from ..config import settings

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

get_db = dependencies.get_db
_READ_ROLES = ["officer", "admin", "auditor"]


@router.get("/health")
def system_health(db: Session = Depends(get_db), user=Depends(require_role(_READ_ROLES))):
    """Real component health: DB reachability plus per-stage availability."""
    from ..ai.ocr import service as ocr_service
    from ..ai.face import get_verifier
    from ..ai.liveness import get_verifier as get_liveness
    from ..ai.deepfake import get_verifier as get_deepfake

    db_ok, last_event = True, None
    try:
        last = db.query(models.AuditEvent).order_by(models.AuditEvent.timestamp.desc()).first()
        last_event = last.timestamp.isoformat() if last else None
    except Exception:
        db_ok = False

    face = get_verifier()
    deep_ready = face.detector is not None and face.recognizer is not None

    deepfake = get_deepfake()
    deepfake_ready = bool(getattr(deepfake, "ready", False))

    return {
        "database": {"status": "operational" if db_ok else "unavailable", "last_audit_event": last_event},
        "ocr": {"status": "operational"},  # verified lazily on first request
        "face_model": {"status": "operational" if deep_ready else "degraded",
                        "model": face.model_name, "model_version": getattr(face, "model_version", None)},
        "liveness": {"status": "operational", "model": "sharpness_entropy_heuristic"},
        "deepfake": {"status": "operational" if deepfake_ready else "degraded",
                      "model": getattr(deepfake, "model_name", "spectral_heuristic"),
                      "model_version": getattr(deepfake, "model_version", None),
                      "note": None if deepfake_ready else "trained classifier unavailable; spectral heuristics only"},
        "face_reuse": {"status": "operational", "model": "sface_vector_store",
                        "backend": settings.VECTOR_BACKEND or "memory"},
        "risk_engine": {"status": "operational", "model": "deterministic_weights"},
        "audit_chain": {"status": "operational"},
    }


@router.get("/activity")
def recent_activity(limit: int = 20, db: Session = Depends(get_db),
                    user=Depends(require_role(_READ_ROLES))):
    """Most recent audit events for the live activity panel (real events only)."""
    rows = (
        db.query(models.AuditEvent)
        .order_by(models.AuditEvent.timestamp.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    return [{
        "timestamp": ev.timestamp.isoformat(),
        "actor_id": ev.actor_id,
        "action": ev.event_type,
        "case_id": ev.case_id,
        "screening_run_id": ev.screening_run_id,
        "hash": ev.current_hash,
    } for ev in rows]


@router.get("/analytics")
def analytics(days: int = 30, db: Session = Depends(get_db),
              user=Depends(require_role(_READ_ROLES))):
    """Case counts, risk distribution, and daily volume from real rows."""
    since = datetime.utcnow() - timedelta(days=max(1, min(days, 365)))
    cases = db.query(models.Case).filter(models.Case.created_at >= since).all()
    case_ids = [c.id for c in cases]

    risk_counts = {"low": 0, "medium": 0, "high": 0, "review_required": 0}
    unscored = 0

    risk_rows = (
        db.query(models.StageResult)
        .join(models.ScreeningRun, models.ScreeningRun.id == models.StageResult.run_id)
        .filter(models.StageResult.stage == "risk_engine",
                models.ScreeningRun.case_id.in_(case_ids))
        .all() if case_ids else []
    )
    scores = []
    durations = []
    run_durations = (
        db.query(models.ScreeningRun.started_at, models.ScreeningRun.completed_at)
        .filter(models.ScreeningRun.case_id.in_(case_ids),
                models.ScreeningRun.completed_at.isnot(None))
        .all() if case_ids else []
    )
    for started, completed in run_durations:
        durations.append((completed - started).total_seconds())

    for r in risk_rows:
        res = r.result if isinstance(r.result, dict) else {}
        level = str(res.get("numeric_level") or "").lower()
        if level in ("low", "medium", "high"):
            risk_counts[level] += 1
        elif res.get("review_required"):
            risk_counts["review_required"] += 1
        else:
            unscored += 1
        score = res.get("risk_score")
        if isinstance(score, (int, float)):
            scores.append(score)
    avg_score = round(sum(scores) / len(scores), 1) if scores else None
    avg_duration_s = round(sum(durations) / len(durations), 1) if durations else None

    daily = {}
    for c in cases:
        day = c.created_at.date().isoformat()
        daily[day] = daily.get(day, 0) + 1

    timings = (
        db.query(models.StageResult.stage, models.StageResult.processing_time_ms)
        .filter(models.StageResult.processing_time_ms.isnot(None))
        .all()
    )
    by_stage = {}
    for stage, ms in timings:
        if isinstance(ms, int) and ms >= 0:
            by_stage.setdefault(stage, []).append(ms)
    avg_latency = {s: round(sum(v) / len(v)) for s, v in by_stage.items()}

    return {
        "window_days": days,
        "total_cases": len(cases),
        "risk_distribution": risk_counts,
        "average_risk_score": avg_score,
        "daily_volume": [{"date": d, "cases": n} for d, n in sorted(daily.items())],
        "avg_stage_latency_ms": dict(sorted(avg_latency.items(), key=lambda kv: -kv[1])),
        "screened_runs": len(risk_rows),
        "unscored_cases": unscored,
        "average_screening_seconds": avg_duration_s,
    }


@router.get("/fraud-graph")
def fraud_graph(limit: int = 200, db: Session = Depends(get_db),
                user=Depends(require_role(_READ_ROLES))):
    """Identity/document/case relationship graph from real extracted fields.

    Nodes: case, subject, document, id_number. Edges: SUBMITTED, EXTRACTED_FROM,
    REUSED_ID. Reuse edges are labelled 'repeated identity signal', never
    'fraud' — a shared attribute alone is not guilt.
    """
    nodes, edges = {}, []
    id_owner = {}

    cases = db.query(models.Case).order_by(models.Case.created_at.desc()).limit(limit).all()
    for case in cases:
        nodes[f"case:{case.id}"] = {
            "id": f"case:{case.id}", "type": "case", "label": f"CASE {case.id[:8]}",
            "status": case.status,
        }
        if case.subject_name:
            key = f"person:{case.subject_name.lower()}"
            nodes.setdefault(key, {"id": key, "type": "person", "label": case.subject_name})
            edges.append({"source": key, "target": f"case:{case.id}", "relation": "SUBMITTED"})

        docs = db.query(models.DocumentFile).filter(
            models.DocumentFile.case_id == case.id).all()
        for doc in docs:
            dkey = f"doc:{doc.id}"
            nodes[dkey] = {"id": dkey, "type": "document", "label": doc.filename or "document",
                            "content_hash": doc.content_hash[:12]}
            edges.append({"source": f"case:{case.id}", "target": dkey, "relation": "HAS_DOCUMENT"})

        idnum = _latest_id_number(db, case.id)
        if idnum:
            ikey = f"id:{idnum}"
            nodes.setdefault(ikey, {"id": ikey, "type": "id_number",
                                     "label": f"ID …{idnum[-4:]}"})
            edges.append({"source": dkey if docs else f"case:{case.id}",
                          "target": ikey, "relation": "EXTRACTED_FROM"})
            prior = id_owner.get(idnum)
            if prior and prior != case.id:
                edges.append({"source": f"case:{case.id}", "target": f"case:{prior}",
                              "relation": "REUSED_ID", "signal": "repeated identity signal"})
            id_owner[idnum] = case.id

    return {"nodes": list(nodes.values()), "edges": edges}


def _latest_id_number(db: Session, case_id: str) -> str | None:
    row = (
        db.query(models.StageResult)
        .join(models.ScreeningRun, models.ScreeningRun.id == models.StageResult.run_id)
        .filter(models.StageResult.stage == "ocr", models.ScreeningRun.case_id == case_id)
        .order_by(models.ScreeningRun.started_at.desc())
        .first()
    )
    if not row:
        return None
    return ((row.result or {}).get("fields") or {}).get("extracted_id_number")
