"""Common FastAPI dependencies.

Provides ``get_db`` session dependency (re‑exported from ``backend.db.database``) and a
``logger`` dependency that adds ``request_id`` to log records.
"""

from __future__ import annotations

from fastapi import Request, Depends

from ..db.database import get_db
from ..utils.logging import logger, get_request_id


def get_logger(request: Request) -> dict:
    # Return a dict of ``extra`` fields to be merged into logger calls.
    return {"request_id": get_request_id(request)}
