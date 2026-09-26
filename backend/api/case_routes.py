"""Case management routes.

Provides endpoints to create a case, list cases, and retrieve a case by ID.
All routes require authentication; creation is limited to ``officer`` role.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ..services import case_service
from ..models import schemas
from ..api import dependencies
from ..security import rbac

router = APIRouter(prefix="/cases", tags=["cases"])

get_db = dependencies.get_db


@router.post("", response_model=schemas.CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: schemas.CaseCreate,
    db=Depends(get_db),
    user=Depends(rbac.require_role(["officer", "admin"])),
):
    new_case = case_service.create_case(db, owner_id=user.id, subject_name=payload.subject_name)
    return case_service.case_to_out(db, new_case)


@router.get("", response_model=List[schemas.CaseOut])
def list_cases(db=Depends(get_db), user=Depends(rbac.require_role(["officer", "admin", "auditor"]))):
    return [case_service.case_to_out(db, c) for c in case_service.list_cases(db)]


@router.get("/{case_id}", response_model=schemas.CaseOut)
def get_case(case_id: str, db=Depends(get_db), user=Depends(rbac.require_role(["officer", "admin", "auditor"]))):
    case = case_service.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case_service.case_to_out(db, case)
