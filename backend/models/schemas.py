"""Pydantic schemas for request and response bodies.

These models mirror the API contracts defined in ``docs/API_CONTRACTS.md``.
"""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CaseCreate(BaseModel):
    subject_name: Optional[str] = None


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    content_hash: str
    file_type: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_at: Optional[datetime] = None


class CaseOut(BaseModel):
    case_id: str
    id: str
    owner_id: str
    subject_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    risk_level: Optional[str] = None
    screening_status: Optional[str] = None
    files: List[FileUploadResponse] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ScreeningRunOut(BaseModel):
    screening_run_id: str
    id: str
    case_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    stage_results: List[dict] = []
    source_file_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AuditEventOut(BaseModel):
    event_id: str = Field(..., alias="id")
    timestamp: datetime
    actor_id: str
    event_type: str
    case_id: Optional[str] = None
    screening_run_id: Optional[str] = None
    previous_hash: str
    current_hash: str
    meta: Optional[dict] = None
    ledger: str = "local_hash_chain"

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HealthResponse(BaseModel):
    status: str = "ok"
