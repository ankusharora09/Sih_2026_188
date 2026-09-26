import asyncio
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

from fastapi import status

from backend.main import app
from backend.config import settings

# Isolate test uploads so pytest does not purge real user uploads
@pytest.fixture(autouse=True, scope="session")
def cleanup_upload_dir(tmp_path_factory):
    orig_dir = settings.UPLOAD_DIR
    test_upload_dir = tmp_path_factory.mktemp("test_uploads")
    settings.UPLOAD_DIR = str(test_upload_dir)
    yield
    settings.UPLOAD_DIR = orig_dir


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:

        resp = await ac.get("/api/v1/health")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_dev_token_and_protected_route():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:

        # Get a dev token for an officer
        token_resp = await ac.post(
            "/api/v1/auth/dev-token",
            json={"user_id": "test-officer", "role": "officer"},
        )
        assert token_resp.status_code == status.HTTP_200_OK
        token = token_resp.json()["access_token"]
        # Use token to create a case
        case_resp = await ac.post(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {token}"},
            json={"subject_name": "John Doe"},
        )
        assert case_resp.status_code == status.HTTP_201_CREATED
        case_id = case_resp.json()["id"]
        # Retrieve the case
        get_resp = await ac.get(
            f"/api/v1/cases/{case_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_resp.status_code == status.HTTP_200_OK
        assert get_resp.json()["subject_name"] == "John Doe"
