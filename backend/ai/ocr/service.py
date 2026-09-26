"""OCR service that attempts PaddleOCR first and falls back to Tesseract.

The ``perform_ocr`` function returns a dictionary containing the OCR output and
metadata about which engine was used.
"""

from __future__ import annotations

import threading
from typing import Dict

from .paddleocr_engine import PaddleOCREngine
from .tesseract_engine import TesseractEngine

# Engines are expensive to construct (PaddleOCR loads DL models); build them
# once and reuse. A lock serializes Paddle inference because the predictor is
# not documented as thread-safe and screening runs execute in worker threads.
_paddle_engine: PaddleOCREngine | None = None
_paddle_lock = threading.Lock()
_tesseract_engine: TesseractEngine | None = None

#: Sentinel dict returned when no OCR engine is available on this system.
_UNAVAILABLE_RESULT: Dict = {
    "engine_used": "none",
    "fallback_used": False,
    "status": "unavailable",
    "result": {
        "raw_text": "",
        "lines": [],
        "confidence": None,
        "engine": "none",
        "processing_time_ms": 0,
    },
}


def perform_ocr(image) -> Dict:
    """Run OCR on ``image`` using PaddleOCR, falling back to Tesseract.

    The returned dictionary contains:
        - ``engine_used``: ``"paddleocr"``, ``"tesseract"``, or ``"none"``
        - ``fallback_used``: ``True`` if Tesseract was used
        - ``status``: ``"success"`` when an engine produced output; ``"unavailable"``
          when neither engine is installed/reachable on this system.
        - ``result``: the raw OCR result dictionary from the engine (or empty dict)
    """

    # Try PaddleOCR first
    global _paddle_engine, _tesseract_engine
    try:
        with _paddle_lock:
            if _paddle_engine is None:
                _paddle_engine = PaddleOCREngine()
            result = _paddle_engine.process(image)
        return {"engine_used": "paddleocr", "fallback_used": False, "status": "success", "result": result}
    except ImportError:
        pass  # Library not installed – try fallback
    except Exception:
        pass  # Runtime failure – try fallback

    # Fallback to Tesseract
    try:
        if _tesseract_engine is None:
            _tesseract_engine = TesseractEngine()
        result = _tesseract_engine.process(image)
        return {"engine_used": "tesseract", "fallback_used": True, "status": "success", "result": result}
    except ImportError:
        pass  # Library not installed
    except Exception:
        pass  # Runtime failure (e.g. tesseract binary missing)

    # Both engines unavailable – return sentinel; caller should record UNAVAILABLE.
    return _UNAVAILABLE_RESULT.copy()

