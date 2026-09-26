"""File upload and retrieval routes.

* ``POST /cases/{case_id}/files`` – upload a document or live capture file.
* ``GET /cases/{case_id}/files`` – list all files for a case.
* ``GET /cases/{case_id}/files/{file_id}/content`` – download/preview bytes.

Both endpoints require authentication. Only ``officer`` and ``admin`` may upload.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse

from ..services import file_service
from ..models import schemas
from ..api import dependencies
from ..security import rbac

router = APIRouter(prefix="/cases", tags=["files"])

get_db = dependencies.get_db


@router.post("/{case_id}/files", response_model=schemas.FileUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    case_id: str,
    file_type: str = "document",
    upload: UploadFile = File(...),
    db=Depends(get_db),
    user=Depends(rbac.require_role(["officer", "admin"])),
):
    from ..services import case_service

    case = case_service.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    doc = file_service.create_file_record(db, case_id=case_id, upload_file=upload, file_type=file_type)
    return schemas.FileUploadResponse(**file_service.file_to_schema(doc))


@router.get("/{case_id}/files", response_model=List[schemas.FileUploadResponse])
def list_files(
    case_id: str,
    db=Depends(get_db),
    user=Depends(rbac.require_role(["officer", "admin", "auditor"])),
):
    from ..services import case_service
    case = case_service.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return [schemas.FileUploadResponse(**file_service.file_to_schema(f)) for f in case.files]


@router.get("/{case_id}/files/{file_id}/content")
def get_file_content(
    case_id: str,
    file_id: str,
    db=Depends(get_db),
    user=Depends(rbac.require_role(["officer", "admin", "auditor"])),
):
    doc = file_service.get_file(db, case_id, file_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    path = Path(doc.stored_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file missing")
    media = doc.mime_type or "application/octet-stream"
    return FileResponse(path=str(path), media_type=media, filename=doc.filename)
