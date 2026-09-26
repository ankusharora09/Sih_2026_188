"""Abstract base class for face verification adapters.

The ``verify`` method receives two images as NumPy arrays (document image
and live‑capture image) and returns a dictionary matching the contract
specified in the Phase 5.1 requirements.
"""

from __future__ import annotations

import abc
from typing import Dict, Any


class FaceVerificationAdapter(abc.ABC):
    """Base class defining the verification interface.

    Implementations must provide a ``verify`` method that returns a mapping
    with the following keys:
        - status ("success" | "failed" | "unavailable")
        - face_detected (bool)
        - faces_count (int)
        - similarity (float | None)
        - match (bool | None)
        - threshold (float)
        - model (str)
        - processing_time_ms (int)
    """

    @abc.abstractmethod
    def verify(self, document_image: Any, live_image: Any) -> Dict[str, Any]:
        """Perform face verification.

        Parameters
        ----------
        document_image: np.ndarray
            The pre‑processed document image.
        live_image: np.ndarray
            The live/selfie image.
        """
        raise NotImplementedError
