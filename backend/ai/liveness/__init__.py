"""Liveness detection package – provides a simple anti‑spoofing verifier.

The ``get_verifier`` function returns an instance of the concrete ``LivenessDetectionAdapter``.
"""

from functools import lru_cache

from .adapter import LivenessDetectionAdapter
from .simple_liveness_adapter import SimpleLivenessAdapter


@lru_cache(maxsize=1)
def get_verifier() -> LivenessDetectionAdapter:
    """Factory that returns the (cached) default simple liveness detector.

    In the future this could be extended to select between multiple implementations.
    """
    return SimpleLivenessAdapter()
