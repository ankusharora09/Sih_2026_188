"""Abstract base class for liveness detection adapters.

Implementations must provide a ``detect`` method that analyses a live capture
image and returns a dictionary with the detection outcome.
"""

from __future__ import annotations

import abc
from typing import Dict, Any


class LivenessDetectionAdapter(abc.ABC):
    @abc.abstractmethod
    def detect(self, live_image: Any) -> Dict[str, Any]:
        """Detect whether the provided image appears to be a live capture.

        Returns a dictionary containing at least:
        - ``status``: ``"success"`` or ``"failed"``
        - ``is_live``: ``True`` if live, ``False`` otherwise
        - ``sharpness``: float variance of Laplacian
        - ``entropy``: float Shannon entropy of pixel histogram
        - ``thresholds``: dict with ``sharpness`` and ``entropy`` thresholds used
        """
        raise NotImplementedError
