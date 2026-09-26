"""Officer decision endpoint — the human-in-the-loop close of a screening.

POST /api/v1/cases/{case_id}/decision
Body: {"action": "verify|review|reject", "note": "..."}
Roles: officer, admin (auditors are read-only).

The decision is recorded on the case and appended to the hash-chained audit
ledger. It never overrides AI evidence — it is the officer's final call.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..db.database import get_db
from ..blockchain.hash_chain import record_audit
from ..security.auth import SimpleUser
from ..security.rbac import require_role
from ..services import case_service

router = APIRouter()

_ALLOWED_ACTIONS = {"verify": "VERIFIED", "review": "REVIEW_REQUIRED", "reject": "REJECTED"}


class DecisionRequest(BaseModel):
    action: str  # verify | review | reject
    note: str = ""


@router.post("/cases/{case_id}/decision", status_code=status.HTTP_200_OK)
def case_decision(
    case_id: str,
    req: DecisionRequest,
    db=Depends(get_db),
    user: SimpleUser = Depends(require_role(["officer", "admin"])),
):
    case = case_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    new_status = _ALLOWED_ACTIONS.get(req.action)
    if new_status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action must be one of: verify, review, reject",
        )

    case.status = new_status
    db.commit()

    event = record_audit(
        db,
        actor_id=user.id,
        event_type=f"officer_decision_{req.action}",
        case_id=case_id,
        meta={"note": req.note[:500], "status": new_status},
    )
    return {
        "case_id": case_id,
        "status": new_status,
        "audit_event_id": event.id,
        "hash": event.current_hash,
    }
