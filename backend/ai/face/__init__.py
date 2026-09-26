"""Face verification package.

Provides a simple Haar‑cascade based face detection and embedding routine.
The public entry point is ``get_verifier`` which returns an instance of
``FaceVerificationAdapter`` ready to be used.
"""

from __future__ import annotations

from functools import lru_cache

from .adapter import FaceVerificationAdapter
from .haar_adapter import HaarFaceVerificationAdapter

@lru_cache(maxsize=1)
def get_verifier() -> FaceVerificationAdapter:
    """Factory returning the (cached) default Haar‑cascade verifier.

    The function isolates the import of OpenCV so that callers can simply
    ``from ..ai.face import get_verifier``.
    """
    return HaarFaceVerificationAdapter()
