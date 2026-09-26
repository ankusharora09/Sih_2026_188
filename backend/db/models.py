"""SQLAlchemy ORM models for the SIH 2026 backend.

The schema follows the design described in ``docs/DATABASE_DESIGN.md`` and uses
UUID primary keys for all main entities. Timestamps are UTC.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey, JSON, LargeBinary, Integer, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from .database import Base

# Table creation is deferred until all models are defined (see end of file)
def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # officer, admin, auditor
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cases = relationship("Case", back_populates="owner")


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True, default=generate_uuid)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    subject_name = Column(String, nullable=True)
    status = Column(String, default="created")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="cases")
    files = relationship("DocumentFile", back_populates="case", cascade="all, delete-orphan")
    runs = relationship("ScreeningRun", back_populates="case", cascade="all, delete-orphan")


class DocumentFile(Base):
    __tablename__ = "document_files"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    content_hash = Column(String, nullable=False)  # SHA‑256 hex digest
    file_type = Column(String, nullable=False)  # document or live_capture
    mime_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="files")


class ScreeningRun(Base):
    __tablename__ = "screening_runs"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    source_file_id = Column(String, nullable=True)
    status = Column(String, default="queued")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    case = relationship("Case", back_populates="runs")
    stage_results = relationship("StageResult", back_populates="run", cascade="all, delete-orphan")


class StageResult(Base):
    __tablename__ = "stage_results"
    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("screening_runs.id"), nullable=False)
    stage = Column(String, nullable=False)
    status = Column(String, nullable=False)  # success, failed, unavailable, skipped
    confidence = Column(String, nullable=True)
    result = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    errors = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    run = relationship("ScreeningRun", back_populates="stage_results")


class FaceEmbedding(Base):
    """Persisted SFace embedding for the document face of a case.

    Only the 128-d normalized vector is stored (not the raw biometric image);
    it powers cross-case face-reuse detection via the vector store.
    """

    __tablename__ = "face_embeddings"
    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    vector_id = Column(String, nullable=False, unique=True)  # id used in the vector store
    embedding = Column(JSON, nullable=False)                 # 128 floats (rounded)
    model_name = Column(String, nullable=False)              # e.g. sface_deep_onnx
    model_version = Column(String, nullable=True)            # e.g. sface_11_aligncrop
    similarity_to_prior = Column(Float, nullable=True)       # cosine vs nearest prior case
    matched_case_id = Column(String, nullable=True)          # nearest prior case, if above threshold
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime, default=datetime.utcnow)
    actor_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    case_id = Column(String, nullable=True)
    screening_run_id = Column(String, nullable=True)
    previous_hash = Column(String, nullable=False)
    current_hash = Column(String, nullable=False)
    meta = Column(JSON, nullable=True)

# After all ORM models are defined, create tables in the database.
from .database import engine
from sqlalchemy import inspect, text

Base.metadata.create_all(engine)


def _ensure_sqlite_columns() -> None:
    """Add columns introduced after the first create_all (SQLite only)."""
    try:
        insp = inspect(engine)
        if "document_files" not in insp.get_table_names():
            return
        cols = {c["name"] for c in insp.get_columns("document_files")}
        with engine.begin() as conn:
            if "mime_type" not in cols:
                conn.execute(text("ALTER TABLE document_files ADD COLUMN mime_type VARCHAR"))
            if "size_bytes" not in cols:
                conn.execute(text("ALTER TABLE document_files ADD COLUMN size_bytes INTEGER"))
            if "screening_runs" in insp.get_table_names():
                run_cols = {c["name"] for c in insp.get_columns("screening_runs")}
                if "source_file_id" not in run_cols:
                    conn.execute(text("ALTER TABLE screening_runs ADD COLUMN source_file_id VARCHAR"))
    except Exception:
        pass


_ensure_sqlite_columns()