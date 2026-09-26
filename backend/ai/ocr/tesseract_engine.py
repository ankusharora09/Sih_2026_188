"""Tesseract OCR engine implementation.

Relies on ``pytesseract``. The path to the ``tesseract`` executable can be
configured via the ``TESSERACT_CMD`` environment variable; if unset, the
default system path is used.
"""

from __future__ import annotations

import os
import time
from typing import List

import cv2
import numpy as np

try:
    import pytesseract
except Exception as e:
    pytesseract = None  # type: ignore

from .base import OCRAdapter


class TesseractEngine(OCRAdapter):
    def __init__(self):
        if pytesseract is None:
            raise ImportError("pytesseract library is not installed")
        
        # Discover tesseract executable path
        tesseract_cmd = os.getenv("TESSERACT_CMD")
        if not tesseract_cmd:
            import shutil
            which_cmd = shutil.which("tesseract")
            if which_cmd:
                tesseract_cmd = which_cmd
            else:
                candidates = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
                ]
                for c in candidates:
                    if os.path.isfile(c):
                        tesseract_cmd = c
                        break
        
        if tesseract_cmd and os.path.isfile(tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def process(self, image: np.ndarray) -> dict:
        import re
        start = time.time()
        if image is None or image.size == 0:
            return {"raw_text": "", "lines": [], "confidence": 0.0, "engine": "tesseract", "processing_time_ms": 0}

        # Handle channels
        if len(image.shape) == 3 and image.shape[2] == 4:
            b, g, r, a = cv2.split(image)
            alpha = a.astype(float) / 255.0
            white = np.ones_like(b) * 255
            bgr = (cv2.merge([b, g, r]) * alpha[:, :, None] + white[:, :, None] * (1.0 - alpha[:, :, None])).astype(np.uint8)
        elif len(image.shape) == 2:
            bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            bgr = image.copy()

        h, w = bgr.shape[:2]
        # Upscale smaller documents to enhance OCR character clarity
        scale = 1.0
        if max(h, w) < 1400:
            scale = 1.5
            bgr = cv2.resize(bgr, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        img_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        # Otsu binarization
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Multi-pass text string extraction (preserves sentences and field lines)
        all_lines: List[str] = []
        seen = set()

        for candidate_img in [otsu, img_rgb]:
            try:
                txt = pytesseract.image_to_string(candidate_img, lang="eng", config="--psm 3")
                for l in txt.splitlines():
                    cl = l.strip()
                    cl_clean = re.sub(r"[^\x20-\x7E\s]", "", cl).strip()
                    if cl_clean and len(cl_clean) > 1 and cl_clean.lower() not in seen:
                        seen.add(cl_clean.lower())
                        all_lines.append(cl_clean)
            except Exception:
                pass

        # Also obtain word-level bounding boxes and confidence scores
        lines: List[dict] = []
        confidences: List[float] = []
        try:
            data = pytesseract.image_to_data(otsu, output_type=pytesseract.Output.DICT)
            n_boxes = len(data.get("text", []))
            for i in range(n_boxes):
                text = data["text"][i].strip()
                conf = data["conf"][i]
                if text:
                    x, y, bw, bh = (
                        data["left"][i],
                        data["top"][i],
                        data["width"][i],
                        data["height"][i],
                    )
                    if scale != 1.0:
                        x, y, bw, bh = int(x / scale), int(y / scale), int(bw / scale), int(bh / scale)
                    lines.append({"text": text, "bbox": [x, y, x + bw, y + bh]})
                    try:
                        c_val = float(conf)
                        if c_val >= 0:
                            confidences.append(c_val)
                    except ValueError:
                        pass
        except Exception:
            pass

        # Fallback if bounding box pass found no words
        if not confidences and all_lines:
            confidences.append(75.0)

        raw_text = "\n".join(all_lines)
        avg_conf = (sum(confidences) / len(confidences)) if confidences else 0.0
        processing_time_ms = int((time.time() - start) * 1000)
        return {
            "raw_text": raw_text,
            "lines": lines,
            "confidence": avg_conf,
            "engine": "tesseract",
            "processing_time_ms": processing_time_ms,
        }
