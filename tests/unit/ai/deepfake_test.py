import numpy as np
import pytest

from backend.ai.deepfake import get_verifier

@pytest.fixture
def verifier():
    return get_verifier()

def test_deepfake_detection_without_live_image(verifier):
    # Create a dummy document image (random)
    doc_img = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)
    result = verifier.detect(doc_img)
    # Should be unavailable when live image is missing
    assert result["status"] == "unavailable"
    assert "model" in result
    assert "latency_ms" in result

def test_deepfake_detection_with_live_image(verifier):
    # Create two different images to simulate manipulation
    doc_img = np.zeros((64, 64, 3), dtype=np.uint8)
    live_img = np.full((64, 64, 3), 255, dtype=np.uint8)
    result = verifier.detect(doc_img, live_img)
    assert result["status"] == "success"
    # Score should be between 0 and 1
    assert 0.0 <= result["score"] <= 1.0
    assert isinstance(result.get("indicators"), list)
    assert "latency_ms" in result
