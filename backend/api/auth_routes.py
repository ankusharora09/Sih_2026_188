"""Authentication routes – development dev‑token endpoint.

POST ``/api/v1/auth/dev-token`` expects a JSON body with ``user_id`` and ``role``
and returns a JWT. In a real deployment this will be replaced with OAuth2/OIDC.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..config import settings
from ..security.auth import create_access_token
from ..models import schemas

router = APIRouter(prefix="/auth", tags=["auth"])


class DevTokenRequest(BaseModel):
    user_id: str
    role: str  # officer, admin, auditor


@router.post("/dev-token", response_model=schemas.TokenResponse)
def dev_token(req: DevTokenRequest):
    # Unauthenticated token minting is a development aid only (Phase 15).
    if not getattr(settings, "AUTH_DEV_TOKEN_ENABLED", False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if req.role not in {"officer", "admin", "auditor"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role – must be officer, admin or auditor",
        )
    token = create_access_token(user_id=req.user_id, role=req.role)
    return {"access_token": token, "token_type": "bearer"}
