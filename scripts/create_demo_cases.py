"""Create demo cases for the Identity Screening API.

This script uses the FastAPI test client to programmatically:
1. Create a new case.
2. Upload a synthetic document image.
3. Optionally upload a live‑capture image.
4. Trigger the screening pipeline.
5. Print the IDs of created objects.
"""

import io
import os
import random
import string
import numpy as np
from fastapi.testclient import TestClient

# Import the FastAPI app
from backend.main import app

client = TestClient(app)

def get_token():
    resp = client.post("/api/v1/auth/dev-token", json={"user_id": "demo-user", "role": "officer"})
    resp.raise_for_status()
    return resp.json()["access_token"]

token = get_token()
client.headers.update({"Authorization": f"Bearer {token}"})

def random_string(length=8):
    return "".join(random.choice(string.ascii_lowercase) for _ in range(length))

def generate_image(width=100, height=100):
    # Simple random noise image saved as PNG bytes
    arr = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    import cv2
    _, buf = cv2.imencode('.png', arr)
    return io.BytesIO(buf.tobytes())

def create_case():
    # For demo, cases are created via a POST to /cases (implementation placeholder).
    # Assuming an endpoint exists: POST /cases with JSON body {"subject": "..."}
    payload = {"subject": f"Demo-{random_string()}"}
    response = client.post("/api/v1/cases", json=payload)
    response.raise_for_status()
    case = response.json()
    return case["id"]

def upload_file(case_id, file_type, image_bytes, filename):
    files = {
        "upload": (filename, image_bytes, "image/png"),
    }
    response = client.post(f"/api/v1/cases/{case_id}/files", params={"file_type": file_type}, files=files)
    response.raise_for_status()
    return response.json()["file_id"]

def trigger_screening(case_id):
    response = client.post(f"/api/v1/cases/{case_id}/screen")
    response.raise_for_status()
    return response.json()["id"]

def main(num_cases=10):
    for i in range(num_cases):
        case_id = create_case()
        doc_img = generate_image()
        doc_file_id = upload_file(case_id, "document", doc_img, f"doc_{i}.png")
        # 50% chance to add a live capture
        if random.random() < 0.5:
            live_img = generate_image()
            upload_file(case_id, "live_capture", live_img, f"live_{i}.png")
        run_id = trigger_screening(case_id)
        print(f"Created case {case_id}, document {doc_file_id}, screening run {run_id}")

if __name__ == "__main__":
    main()
