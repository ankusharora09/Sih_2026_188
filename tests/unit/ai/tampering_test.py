import numpy as np
import pytest

from backend.ai.tampering import get_verifier

@pytest.fixture
def verifier():
    return get_verifier()

def test_tampering_low_score(verifier):
    # Uniform image – low variance => score near 0, not tampered.
    img = np.full((64, 64, 3), 128, dtype=np.uint8)
    result = verifier.detect(img)
    assert result["status"] == "success"
    assert result["tampered"] is False
    assert result["score"] == 0.0

def test_tampering_high_score(verifier):
    # Random noise image – high variance => score higher than threshold.
    img = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)
    result = verifier.detect(img)
    assert result["status"] == "success"
    # Score should be > 0 (and likely >= threshold, making tampered True)
    assert result["score"] > 0
    assert isinstance(result["tampered"], bool)
