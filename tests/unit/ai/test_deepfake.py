import numpy as np
import pytest
from backend.ai.deepfake import get_verifier

@pytest.fixture
def deepfake_verifier():
    return get_verifier()

def test_deepfake_unavailable(deepfake_verifier):
    # When live image is not provided, should return unavailable status
    doc_img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = deepfake_verifier.detect(doc_img)
    assert result["status"] == "unavailable"
    assert "model" in result

def test_deepfake_success(monkeypatch, deepfake_verifier):
    # Force _mse to return low score (< threshold)
    monkeypatch.setattr(deepfake_verifier, "_mse", lambda a, b: 0.05)
    doc_img = np.zeros((100, 100, 3), dtype=np.uint8)
    live_img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = deepfake_verifier.detect(doc_img, live_img)
    assert result["status"] == "success"
    assert "score" in result
    # Since score is below threshold, indicators should be empty
    assert result.get("indicators", []) == []

def test_deepfake_no_live(deepfake_verifier):
    doc_img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = deepfake_verifier.detect(doc_img)
    assert result["status"] == "unavailable"
