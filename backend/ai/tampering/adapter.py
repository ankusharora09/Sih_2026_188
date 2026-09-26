"""Abstract base class for tampering detection adapters.

Implementations must provide a ``detect`` method that analyses an image and
returns a dictionary with detection details.
"""

from __future__ import annotations

import abc
from typing import Dict, Any


class TamperingDetectionAdapter(abc.ABC):
    @abc.abstractmethod
    def detect(self, document_image: Any) -> Dict[str, Any]:
        """Detect tampering in the given document image.

        Returns a dictionary containing at least:
        - ``status``: ``"success"`` or ``"failed"``
        - ``tampered``: ``True``/``False``/``None``
        - ``score``: float 0‑1 confidence
        - ``regions``: list of suspect regions (empty for demo)
        - ``signals``: list of heuristic signals detected
        """
        raise NotImplementedError
