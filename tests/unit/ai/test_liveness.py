import numpy as np
import pytest
from backend.ai.liveness import get_verifier

@pytest.fixture
def liveness_verifier():
    return get_verifier()

def test_liveness_live(monkeypatch, liveness_verifier):
    # Mock sharpness and entropy to be high
    monkeypatch.setattr(liveness_verifier, "_sharpness", lambda img: 150.0)
    monkeypatch.setattr(liveness_verifier, "_entropy", lambda img: 10.0)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = liveness_verifier.detect(img)
    assert result["status"] == "success"
    assert result["is_live"] is True
    assert result["sharpness"] == 150.0
    assert result["entropy"] == 10.0

def test_liveness_spoof(monkeypatch, liveness_verifier):
    monkeypatch.setattr(liveness_verifier, "_sharpness", lambda img: 50.0)
    monkeypatch.setattr(liveness_verifier, "_entropy", lambda img: 2.0)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = liveness_verifier.detect(img)
    assert result["status"] == "success"
    assert result["is_live"] is False
    assert result["sharpness"] == 50.0
    assert result["entropy"] == 2.0

def test_liveness_unavailable(monkeypatch, liveness_verifier):
    # Simulate exception in processing
    monkeypatch.setattr(liveness_verifier, "_sharpness", lambda img: 1/0)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = liveness_verifier.detect(img)
    assert result["status"] == "failed"
    assert "error" in result
