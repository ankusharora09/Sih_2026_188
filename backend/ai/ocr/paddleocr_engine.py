"""PaddleOCR engine implementation.

If PaddleOCR cannot be imported, the class raises an ``ImportError`` at
initialisation. ``process`` returns a dictionary matching the contract defined
in ``backend/ai/ocr/base.py``.
"""

from __future__ import annotations

import time
from typing import List

import cv2
import numpy as np

# Import PaddleOCR lazily – the import may fail on systems without the library.
try:
    from paddleocr import PaddleOCR
except Exception as e:
    PaddleOCR = None  # type: ignore

from .base import OCRAdapter


class PaddleOCREngine(OCRAdapter):
    def __init__(self, **kwargs):
        if PaddleOCR is None:
            raise ImportError("PaddleOCR library is not installed")
        # Initialise PaddleOCR with default (English) model; additional args can be passed.
        self.ocr = PaddleOCR(use_angle_cls=True, lang="en", **kwargs)

    def process(self, image: np.ndarray) -> dict:
        start = time.time()
        # PaddleOCR expects a BGR image; ensure we have one.
        if len(image.shape) == 2:
            # Convert grayscale to BGR for consistency.
            img_bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            img_bgr = image

        result = self.ocr.ocr(img_bgr, cls=True)
        # ``result`` is a list of pages; we take the first page.
        lines: List[dict] = []
        raw_text_parts: List[str] = []
        confidences: List[float] = []
        for line in result[0]:
            # line format: ([x0, y0, x1, y1, ...], (text, confidence))
            bbox = line[0]
            text, conf = line[1]
            lines.append({"text": text, "bbox": bbox})
            raw_text_parts.append(text)
            confidences.append(float(conf))

        raw_text = "\n".join(raw_text_parts)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        processing_time_ms = int((time.time() - start) * 1000)
        return {
            "raw_text": raw_text,
            "lines": lines,
            "confidence": avg_conf,
            "engine": "paddleocr",
            "processing_time_ms": processing_time_ms,
        }
