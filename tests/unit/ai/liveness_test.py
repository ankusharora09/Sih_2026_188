import numpy as np
import pytest

from backend.ai.liveness import get_verifier

@pytest.fixture
def verifier():
    return get_verifier()

def test_liveness_live_image(verifier):
    # Create a random noisy image (simulating a live capture)
    img = (np.random.rand(64, 64, 3) * 255).astype(np.uint8)
    result = verifier.detect(img)
    assert result["status"] == "success"
    # With random noise, sharpness and entropy should be high enough to be considered live.
    assert result["is_live"] is True
    assert isinstance(result["sharpness"], float)
    assert isinstance(result["entropy"], float)

def test_liveness_non_live_image(verifier):
    # Uniform gray image – low variance and low entropy
    img = np.full((64, 64, 3), 128, dtype=np.uint8)
    result = verifier.detect(img)
    assert result["status"] == "success"
    assert result["is_live"] is False
    # Sharpness should be near zero, entropy low
    assert result["sharpness"] < 1e-3
    assert result["entropy"] < 1e-3
