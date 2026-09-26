"""File service – validation, storage and DB record creation for uploads.

The service validates size, extension, computes SHA‑256 while streaming to disk,
generates a safe filename, and creates a ``DocumentFile`` record linked to a case.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile, HTTPException, status
from werkzeug.utils import secure_filename

from sqlalchemy.orm import Session

from ..config import settings
from ..db import models


def file_to_schema(doc: models.DocumentFile) -> dict:
    return {
        "file_id": doc.id,
        "filename": doc.filename,
        "content_hash": doc.content_hash,
        "file_type": doc.file_type,
        "mime_type": doc.mime_type,
        "size_bytes": doc.size_bytes,
        "uploaded_at": doc.uploaded_at,
    }


def _validate_file(upload_file: UploadFile) -> None:
    ext = Path(upload_file.filename or "").suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' not allowed",
        )
    try:
        import magic
        mime = magic.from_buffer(upload_file.file.read(2048), mime=True)
        upload_file.file.seek(0)
        allowed_mimes = getattr(
            settings,
            "ALLOWED_MIME_TYPES",
            ["application/pdf", "image/jpeg", "image/png", "image/tiff"],
        )
        if mime not in allowed_mimes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MIME type '{mime}' not allowed",
            )
    except ImportError:
        pass


def _save_file(file_obj: UploadFile) -> tuple[str, str, int]:
    """Save the uploaded file to ``settings.upload_path``.

    Returns ``(stored_path, sha256_hex, size_bytes)``.
    """
    upload_dir = settings.upload_path
    suffix = Path(file_obj.filename or "").suffix.lower()
    safe_name = f"{uuid4()}{suffix}"
    dest_path = upload_dir / safe_name
    hasher = hashlib.sha256()
    total_bytes = 0
    try:
        with dest_path.open("wb") as out_file:
            while True:
                chunk = file_obj.file.read(8192)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Uploaded file exceeds maximum allowed size",
                    )
                out_file.write(chunk)
                hasher.update(chunk)
    except HTTPException:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise
    return str(dest_path), hasher.hexdigest(), total_bytes


def create_file_record(
    db: Session,
    case_id: str,
    upload_file: UploadFile,
    file_type: str,
) -> models.DocumentFile:
    _validate_file(upload_file)
    stored_path, file_hash, size_bytes = _save_file(upload_file)
    filename = secure_filename(upload_file.filename or "") or "upload"
    doc = models.DocumentFile(
        id=str(uuid4()),
        case_id=case_id,
        filename=filename,
        stored_path=stored_path,
        content_hash=file_hash,
        file_type=file_type,
        mime_type=upload_file.content_type,
        size_bytes=size_bytes,
    )
    try:
        db.add(doc)
        case = db.query(models.Case).filter(models.Case.id == case_id).first()
        if case and case.status in (None, "created"):
            case.status = "uploaded"
        db.commit()
        db.refresh(doc)
    except Exception:
        db.rollback()
        p = Path(stored_path)
        if p.exists():
            p.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist uploaded file",
        )
    return doc


def get_file(db: Session, case_id: str, file_id: str) -> models.DocumentFile | None:
    return (
        db.query(models.DocumentFile)
        .filter(models.DocumentFile.id == file_id, models.DocumentFile.case_id == case_id)
        .first()
    )
