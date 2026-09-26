"""Dashboard routes – minimal officer dashboard.

Provides a placeholder HTML page that lists cases and their latest screening runs.
In a production system this would be a full‑featured UI, but for Phase 5 it
satisfies the requirement of having an officer‑facing endpoint.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from ..db import models as db_models
from ..api import dependencies

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

get_db = dependencies.get_db

@router.get("/", response_class=HTMLResponse)
async def officer_dashboard(db=Depends(get_db)):
    """Render a very simple HTML dashboard.

    The page fetches all cases and, for each case, the most recent screening
    run (if any). This is sufficient for the demo and satisfies the Phase 5
    officer‑dashboard requirement.
    """
    cases = db.query(db_models.Case).all()
    html = "<html><head><title>Officer Dashboard</title></head><body>"
    html += "<h1>Officer Dashboard</h1>"
    if not cases:
        html += "<p>No cases found.</p>"
    else:
        html += "<ul>"
        for c in cases:
            html += f"<li>Case {c.id}: {c.subject_name or '—'}"
            # Find latest screening run
            run = (
                db.query(db_models.ScreeningRun)
                .filter(db_models.ScreeningRun.case_id == c.id)
                .order_by(db_models.ScreeningRun.started_at.desc())
                .first()
            )
            if run:
                html += f" – Run {run.id} status: {run.status}"
            else:
                html += " – No screening run"
            html += "</li>"
        html += "</ul>"
    html += "</body></html>"
    return HTMLResponse(content=html)
