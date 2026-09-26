"""Base class for OCR adapters.

Concrete adapters must implement a ``process`` method that receives a NumPy
image array and returns a dictionary with the OCR result.
"""

from __future__ import annotations

import abc
import numpy as np


class OCRAdapter(abc.ABC):
    @abc.abstractmethod
    def process(self, image: np.ndarray) -> dict:
        """Run OCR on ``image`` and return a result dictionary.

        The result should contain at least:
            - ``raw_text`` (str)
            - ``lines`` (list of dicts with ``text`` and ``bbox``)
            - ``confidence`` (float average confidence if available)
            - ``engine`` (name of the engine used)
        """
        raise NotImplementedError
