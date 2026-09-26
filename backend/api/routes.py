"""Root API router – aggregates sub-routers and applies version prefix.

All routes are served under ``/api/v1``.

Note: ``case_detail_routes`` serves the HTML page at ``/cases/{case_id}`` and is
mounted directly on the main ``app`` in ``main.py``, NOT here, to avoid
conflicting with the JSON API at ``/api/v1/cases/{case_id}``.
"""

from __future__ import annotations

from fastapi import APIRouter

from . import auth_routes, case_routes, file_routes, screening_routes, dashboard_routes
from . import intelligence_routes, decision_routes


router = APIRouter(prefix="/api/v1")
router.include_router(auth_routes.router)
router.include_router(case_routes.router)
router.include_router(file_routes.router)
router.include_router(screening_routes.router)
router.include_router(dashboard_routes.router)
router.include_router(intelligence_routes.router)
router.include_router(decision_routes.router)
