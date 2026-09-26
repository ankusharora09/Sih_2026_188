import asyncio
import io
import numpy as np
import cv2
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import status

from backend.main import app
from backend.config import settings

@pytest.mark.asyncio
async def test_full_screening_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Obtain dev token for officer
        token_resp = await ac.post("/api/v1/auth/dev-token", json={"user_id": "officer1", "role": "officer"})
        assert token_resp.status_code == status.HTTP_200_OK
        token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a new case
        case_resp = await ac.post("/api/v1/cases", headers=headers, json={"subject_name": "Test Subject"})
        assert case_resp.status_code == status.HTTP_201_CREATED
        case_id = case_resp.json()["id"]

        # Generate a synthetic document image (white square)
        img = np.full((100, 100, 3), 255, dtype=np.uint8)
        _, img_buf = cv2.imencode('.png', img)
        img_bytes = img_buf.tobytes()
        files = {"upload": ("doc.png", img_bytes, "image/png")}
        # Upload document file
        upload_resp = await ac.post(f"/api/v1/cases/{case_id}/files", headers=headers, params={"file_type": "document"}, files=files)
        assert upload_resp.status_code == status.HTTP_201_CREATED

        # Trigger screening run (202 = accepted; stages execute in background)
        screen_resp = await ac.post(f"/api/v1/cases/{case_id}/screen", headers=headers)
        assert screen_resp.status_code == status.HTTP_202_ACCEPTED
        assert screen_resp.json()["status"] in {"queued", "running"}
        first_run_id = screen_resp.json()["id"]

        # Re-triggering while the run is active is IDEMPOTENT: the existing run
        # is returned (202) instead of starting a second pipeline.
        conflict_resp = await ac.post(f"/api/v1/cases/{case_id}/screen", headers=headers)
        assert conflict_resp.status_code == status.HTTP_202_ACCEPTED
        assert conflict_resp.json()["id"] == first_run_id

        # Poll until the run finishes (max ~60s)
        data = None
        for _ in range(40):
            await asyncio.sleep(1.5)
            poll_resp = await ac.get(f"/api/v1/cases/{case_id}/screening", headers=headers)
            if poll_resp.status_code == status.HTTP_200_OK:
                data = poll_resp.json()
                if data["status"] not in {"queued", "running"}:
                    break
        assert data is not None and data["status"] in {"completed", "failed"}

        # Verify that stage_results contain expected stages
        stages = {sr["stage"] for sr in data["stage_results"]}
        expected = {"preprocessing", "ocr", "liveness_detection", "tampering_detection", "face_verification", "deepfake_detection", "anomaly_detection", "risk_engine", "explanation"}
        assert expected.issubset(stages)
        # Ensure no stage has status "failed" unless preprocessing itself failed
        for sr in data["stage_results"]:
            if sr["stage"] != "preprocessing":
                assert sr["status"] != "failed"
        # Numeric timing column round-trips
        timings = [sr["processing_time_ms"] for sr in data["stage_results"]]
        assert all(t is None or isinstance(t, int) for t in timings)
