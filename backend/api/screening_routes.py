"""Screening routes – triggers the pipeline and exposes audit/hash-chain endpoints.

Endpoints:
  POST /cases/{case_id}/screen    – start screening run
  GET  /cases/{case_id}/screening – get latest run
  GET  /cases/{case_id}/audit     – list audit events for case
  GET  /cases/{case_id}/audit/verify – verify hash-chain integrity
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ..services import screening_service
from ..db import models as db_models
from ..models import schemas
from ..api import dependencies
from ..security import rbac

router = APIRouter(prefix="/cases", tags=["screening"])

get_db = dependencies.get_db


@router.post("/{case_id}/screen", response_model=schemas.ScreeningRunOut, status_code=status.HTTP_202_ACCEPTED)
def start_screening(
    case_id: str,
    db=Depends(get_db),
    user=Depends(rbac.require_role(["officer", "admin"])),
):
    """Enqueue a screening run and return immediately (202 Accepted).

    Idempotent: if the case already has a queued/running run, that existing
    run is returned instead of starting a second one, so a UI retry or a
    double-fired request can never duplicate the pipeline.
    """
    from ..services import case_service
    case = case_service.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    try:
        run = screening_service.create_screening_run(db, case_id=case_id, actor_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    payload = screening_service.serialize_run(run)
    return schemas.ScreeningRunOut(**payload)

@router.get("/{case_id}/screening", response_model=schemas.ScreeningRunOut)
def get_screening(case_id: str, db=Depends(get_db), user=Depends(rbac.require_role(["officer", "admin", "auditor"]))):
    # Get latest screening run for case
    run = (
        db.query(db_models.ScreeningRun)
        .filter(db_models.ScreeningRun.case_id == case_id)
        .order_by(db_models.ScreeningRun.started_at.desc())
        .first()
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screening run not found")
    payload = screening_service.serialize_run(run)
    return schemas.ScreeningRunOut(**payload)


@router.get("/{case_id}/audit", response_model=List[schemas.AuditEventOut])
def list_audit_events(
    case_id: str,
    db=Depends(get_db),
    user=Depends(rbac.require_role(["officer", "admin", "auditor"])),
):
    """Return all audit events associated with ``case_id`` in chronological order."""
    from ..services import case_service
    case = case_service.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    events = (
        db.query(db_models.AuditEvent)
        .filter(db_models.AuditEvent.case_id == case_id)
        .order_by(db_models.AuditEvent.timestamp.asc())
        .all()
    )
    return [
        schemas.AuditEventOut(
            id=ev.id,
            timestamp=ev.timestamp,
            actor_id=ev.actor_id,
            event_type=ev.event_type,
            case_id=ev.case_id,
            screening_run_id=ev.screening_run_id,
            previous_hash=ev.previous_hash,
            current_hash=ev.current_hash,
            meta=ev.meta,
        )
        for ev in events
    ]


@router.get("/{case_id}/audit/verify")
def verify_audit_chain(
    case_id: str,
    db=Depends(get_db),
    user=Depends(rbac.require_role(["officer", "admin", "auditor"])),
):
    """Verify the hash-chain integrity for all audit events in the database.

    Returns a JSON object with:
    - ``valid``: True if the entire chain is consistent
    - ``ledger``: always ``"local_hash_chain"``
    - ``note``: human-readable explanation
    """
    from ..blockchain.hash_chain import HashChain
    chain = HashChain(db)
    valid = chain.verify_chain()
    return {
        "valid": valid,
        "ledger": "local_hash_chain",
        "note": (
            "Hash-chain integrity verified. All audit events are consistent."
            if valid
            else "Hash-chain integrity check FAILED. Potential tampering detected."
        ),
    }

