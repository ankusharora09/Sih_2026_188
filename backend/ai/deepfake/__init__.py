"""Deepfake detection package – adapters for image/video manipulation detection."""

from functools import lru_cache

from .adapter import DeepfakeDetectionAdapter
from .simple_deepfake_adapter import SimpleDeepfakeAdapter


@lru_cache(maxsize=1)
def get_verifier() -> DeepfakeDetectionAdapter:
    """Factory that returns the (cached) default deepfake detector.

    Prefers the trained ResNet18 forgery classifier (models/document_forgery_gt2.pth,
    trained on the Genuine/Tampered 2 dataset); falls back to the spectral-heuristic
    adapter when torch or the checkpoint is unavailable.
    """
    from .trained_forgery_adapter import TrainedForgeryDeepfakeAdapter

    try:
        trained = TrainedForgeryDeepfakeAdapter()
        if trained.ready:
            return trained
    except Exception:
        pass
    return SimpleDeepfakeAdapter()
