"""Regression tests: duplicate screening execution must be impossible.

Covers the UI-loop root cause at the API layer:
- Rapid duplicate POST /screen calls return the SAME run id (no duplicate
  worker threads, no second pipeline) — the check-then-act race fix.
- Creation is idempotent once a run is already active.
- After completion, an explicit re-screen creates exactly one NEW run
  (old runs never restart; new runs get fresh ids).
"""

import asyncio
import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status

from backend.main import app
from backend.db import models as db_models
from backend.db.database import SessionLocal


async def _headers_for(ac: AsyncClient, role: str = "officer"):
    """Mint a token through the dev-token endpoint (same path the UI uses)."""
    r = await ac.post("/api/v1/auth/dev-token", json={"user_id": "idem-tester", "role": role})
    assert r.status_code == status.HTTP_200_OK, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _mkcase(ac: AsyncClient, headers, name: str) -> str:
    r = await ac.post("/api/v1/cases", headers=headers, json={"subject_name": name})
    assert r.status_code == status.HTTP_201_CREATED, r.text
    return r.json()["id"]


def _run_ids(case_id: str) -> list[str]:
    db = SessionLocal()
    try:
        rows = (
            db.query(db_models.ScreeningRun)
            .filter(db_models.ScreeningRun.case_id == case_id)
            .all()
        )
        return [r.id for r in rows]
    finally:
        db.close()


@pytest.mark.asyncio
async def test_duplicate_screen_calls_yield_single_run():
    """Firing N concurrent POST /screen requests must create exactly ONE run."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = await _headers_for(ac)
        case_id = await _mkcase(ac, headers, "Idempotency Race")

        responses = await asyncio.gather(
            *[ac.post(f"/api/v1/cases/{case_id}/screen", headers=headers) for _ in range(5)]
        )

        for r in responses:
            assert r.status_code == status.HTTP_202_ACCEPTED, r.text

        run_ids = {r.json()["id"] for r in responses}
        assert len(run_ids) == 1, f"expected ONE run, got {len(run_ids)}: {run_ids}"

        db_ids = _run_ids(case_id)
        assert len(db_ids) == 1, f"DB must hold exactly one run row, got {len(db_ids)}"

        # Let the worker drain so the test DB stays clean for other suites.
        for _ in range(60):
            poll = await ac.get(f"/api/v1/cases/{case_id}/screening", headers=headers)
            if poll.status_code == 200 and poll.json()["status"] not in {"queued", "running"}:
                break
            await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_completed_run_never_restarts_implicitly():
    """Polling/reading a completed run must not spawn new runs; only an explicit
    POST /screen after completion creates a new (distinct) run."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = await _headers_for(ac)
        case_id = await _mkcase(ac, headers, "Idempotency Completed")

        first = await ac.post(f"/api/v1/cases/{case_id}/screen", headers=headers)
        assert first.status_code == status.HTTP_202_ACCEPTED
        first_id = first.json()["id"]

        # Poll until terminal.
        final = None
        for _ in range(60):
            poll = await ac.get(f"/api/v1/cases/{case_id}/screening", headers=headers)
            if poll.status_code == 200 and poll.json()["status"] not in {"queued", "running"}:
                final = poll.json()
                break
            await asyncio.sleep(0.5)
        assert final is not None and final["id"] == first_id
        assert final["status"] in {"completed", "failed"}

        runs_before = set(_run_ids(case_id))

        # Idempotent re-reads: GET /screening must keep returning the SAME run.
        for _ in range(3):
            again = await ac.get(f"/api/v1/cases/{case_id}/screening", headers=headers)
            assert again.status_code == 200
            assert again.json()["id"] == first_id
        assert set(_run_ids(case_id)) == runs_before, "polling spawned extra runs"

        # The single explicit action allowed now: start a NEW run.
        second = await ac.post(f"/api/v1/cases/{case_id}/screen", headers=headers)
        assert second.status_code == status.HTTP_202_ACCEPTED
        assert second.json()["id"] != first_id

        # NOTE: "idempotent while active" for THIS second run is not asserted
        # here — a document-less pipeline finishes in milliseconds, so the run
        # may already be terminal (correctly admitting a new run) before the
        # next request arrives. Concurrent dedup is proven deterministically
        # by test_duplicate_screen_calls_yield_single_run.

        for _ in range(60):
            poll = await ac.get(f"/api/v1/cases/{case_id}/screening", headers=headers)
            if poll.status_code == 200 and poll.json()["status"] not in {"queued", "running"}:
                break
            await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_worker_body_ignores_duplicate_invocation():
    """Direct service-level guard: _execute_run on a non-queued run is a no-op."""
    from backend.services import screening_service

    db = SessionLocal()
    try:
        case_id = uuid.uuid4().hex
        db.add(db_models.Case(id=case_id, owner_id="t", subject_name="Worker Guard"))
        run = db_models.ScreeningRun(id=uuid.uuid4().hex, case_id=case_id,
                                     status="completed",
                                     started_at=__import__("datetime").datetime.utcnow())
        db.add(run)
        db.commit()
        run_id = run.id  # capture before close — commit expires attributes
    finally:
        db.close()

    # Must return without re-executing or changing the run's terminal status.
    screening_service._execute_run(run_id, case_id, "tester")

    db = SessionLocal()
    try:
        row = db.query(db_models.ScreeningRun).filter(db_models.ScreeningRun.id == run.id).first()
        assert row.status == "completed"
        stages = db.query(db_models.StageResult).filter(db_models.StageResult.run_id == run.id).all()
        assert stages == []
    finally:
        db.close()
