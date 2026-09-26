import numpy as np
import pytest
from backend.ai.face import get_verifier

@pytest.fixture
def verifier():
    return get_verifier()

def test_face_verification_success_match(monkeypatch, verifier):
    # Mock detection to return a single face ROI for both images (identical arrays)
    dummy_roi = np.ones((64, 64), dtype=np.uint8)
    monkeypatch.setattr(verifier, "_detect_faces", lambda img: [dummy_roi])
    # Mock embed to produce a unit vector of ones (normalized)
    monkeypatch.setattr(verifier, "_embed", lambda roi: np.ones(4096) / np.linalg.norm(np.ones(4096)))
    doc_img = np.zeros((100, 100, 3), dtype=np.uint8)
    live_img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = verifier.verify(doc_img, live_img)
    assert result["status"] == "success"
    assert result["face_detected"] is True
    assert result["similarity"] == pytest.approx(1.0, rel=1e-5)
    assert result["match"] is True

def test_face_verification_success_mismatch(monkeypatch, verifier):
    # Different ROIs produce orthogonal vectors -> similarity ~0
    roi_a = np.ones((64, 64), dtype=np.uint8)
    roi_b = np.zeros((64, 64), dtype=np.uint8)
    def detect_a(img):
        return [roi_a]
    def detect_b(img):
        return [roi_b]
    # Alternate return based on image identity via id
    monkeypatch.setattr(verifier, "_detect_faces", lambda img: detect_a(img) if img.shape[0] == 100 else detect_b(img))
    # Embedding will be normalized arrays
    monkeypatch.setattr(verifier, "_embed", lambda roi: (roi.astype(np.float32).flatten() / np.linalg.norm(roi.astype(np.float32).flatten())) if np.linalg.norm(roi.astype(np.float32).flatten()) != 0 else roi.astype(np.float32).flatten())
    doc_img = np.zeros((100, 100, 3), dtype=np.uint8)  # will get roi_a
    live_img = np.zeros((200, 200, 3), dtype=np.uint8)  # will get roi_b (different shape triggers detection path)
    result = verifier.verify(doc_img, live_img)
    assert result["status"] == "success"
    assert result["face_detected"] is True
    assert result["similarity"] == pytest.approx(0.0, abs=1e-5)
    assert result["match"] is False

def test_face_verification_no_face(monkeypatch, verifier):
    # Mock detection to return empty list for document image
    monkeypatch.setattr(verifier, "_detect_faces", lambda img: [] )
    doc_img = np.zeros((100, 100, 3), dtype=np.uint8)
    live_img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = verifier.verify(doc_img, live_img)
    assert result["status"] == "success"
    assert result["face_detected"] is False
    assert result["similarity"] is None
    assert result["match"] is None
