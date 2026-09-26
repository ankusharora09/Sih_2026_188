"""Case service – business logic for case CRUD operations.

Uses a SQLAlchemy ``Session`` instance injected via FastAPI dependencies.
"""

from __future__ import annotations

from uuid import uuid4
from typing import List, Optional

from sqlalchemy.orm import Session

from ..db import models
from ..services import file_service
from ..models import schemas


def create_case(db: Session, owner_id: str, subject_name: str | None = None) -> models.Case:
    new_case = models.Case(
        id=str(uuid4()),
        owner_id=owner_id,
        subject_name=subject_name,
        status="created",
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return new_case


def list_cases(db: Session, skip: int = 0, limit: int = 1000) -> List[models.Case]:
    return db.query(models.Case).order_by(models.Case.created_at.desc()).offset(skip).limit(limit).all()


def get_case(db: Session, case_id: str) -> models.Case | None:
    return db.query(models.Case).filter(models.Case.id == case_id).first()


def latest_run(db: Session, case_id: str) -> Optional[models.ScreeningRun]:
    return (
        db.query(models.ScreeningRun)
        .filter(models.ScreeningRun.case_id == case_id)
        .order_by(models.ScreeningRun.started_at.desc())
        .first()
    )


def derive_risk(db: Session, case: models.Case) -> tuple[str, Optional[str]]:
    run = latest_run(db, case.id)
    if not run:
        return "Not screened", None
    if run.status == "queued":
        return "Pending", run.status
    if run.status == "failed":
        return "Unavailable", run.status
    risk_stage = (
        db.query(models.StageResult)
        .filter(models.StageResult.run_id == run.id, models.StageResult.stage == "risk_engine")
        .first()
    )
    if risk_stage and isinstance(risk_stage.result, dict):
        return risk_stage.result.get("risk_level") or "N/A", run.status
    return "N/A", run.status


def case_to_out(db: Session, case: models.Case) -> schemas.CaseOut:
    risk, screening_status = derive_risk(db, case)
    return schemas.CaseOut(
        case_id=case.id,
        id=case.id,
        owner_id=case.owner_id,
        subject_name=case.subject_name,
        status=case.status,
        created_at=case.created_at,
        updated_at=case.updated_at,
        risk_level=risk,
        screening_status=screening_status,
        files=[schemas.FileUploadResponse(**file_service.file_to_schema(f)) for f in case.files],
    )
