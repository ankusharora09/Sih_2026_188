import numpy as np
import pytest
from backend.ai.tampering import get_verifier

@pytest.fixture
def tamper_verifier():
    return get_verifier()

def test_tampering_clean(monkeypatch, tamper_verifier):
    # Mock _score to return low (clean)
    monkeypatch.setattr(tamper_verifier, "_score", lambda img: 0.1)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = tamper_verifier.detect(img)
    assert result["status"] == "success"
    assert result["tampered"] is False
    assert isinstance(result["score"], float)

def test_tampering_tampered(monkeypatch, tamper_verifier):
    monkeypatch.setattr(tamper_verifier, "_score", lambda img: 0.9)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = tamper_verifier.detect(img)
    assert result["status"] == "success"
    assert result["tampered"] is True
    assert isinstance(result["score"], float)

def test_tampering_unavailable(monkeypatch, tamper_verifier):
    monkeypatch.setattr(tamper_verifier, "_score", lambda img: 1/0)
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    result = tamper_verifier.detect(img)
    assert result["status"] == "failed"
    assert "error" in result
