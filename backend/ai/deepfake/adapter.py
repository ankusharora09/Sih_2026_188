"""Abstract base class for deepfake detection adapters.

Implementations must provide a ``detect`` method that analyses a document image
and an optional live capture image (or video frames) and returns a structured
result.
"""

from __future__ import annotations

import abc
from typing import Any, Dict


class DeepfakeDetectionAdapter(abc.ABC):
    @abc.abstractmethod
    def detect(self, document_image: Any, live_image: Any = None) -> Dict[str, Any]:
        """Detect deepfake/manipulation.

        Returns a dictionary with at least the following keys:
        - ``status``: ``"success"``, ``"unavailable"`` or ``"failed"``
        - ``score``: float 0‑1 indicating likelihood of manipulation (higher = more likely)
        - ``indicators``: list of strings describing heuristics used
        - ``model``: name of the underlying model/approach
        - ``latency_ms``: processing time in milliseconds
        - ``error`` (optional): error message if status is ``failed``
        """
        raise NotImplementedError
