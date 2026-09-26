"""Image quality analysis utilities.

Provides a function ``analyze_quality`` that returns a dictionary of
metrics used by the Phase 4 preprocessing stage.
"""

from __future__ import annotations

import cv2
import numpy as np


def analyze_quality(image: np.ndarray) -> dict:
    """Analyze basic image quality metrics.

    The function returns a dictionary containing:

    - ``resolution``: ``{"width": int, "height": int}``
    - ``blur_score``: variance of Laplacian (higher = sharper)
    - ``brightness``: mean pixel intensity (0‑255)
    - ``contrast``: standard deviation of pixel intensity
    - ``quality_score``: simple aggregate (0‑1) based on thresholds
    - ``quality_status``: ``"good"`` or ``"poor"``
    - ``warnings``: list of strings for any metric outside acceptable range
    """

    # Ensure we work with a grayscale image for most metrics
    if len(image.shape) == 3:
        # Color image (BGR or RGB) - convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif len(image.shape) == 4:
        # RGBA image - convert to BGR then to grayscale
        bgr = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    else:
        # Already grayscale or other format
        gray = image
    height, width = gray.shape[:2]

    # Blur detection – Laplacian variance
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blur_score = float(laplacian.var())

    # Brightness & contrast (on grayscale)
    brightness = float(gray.mean())
    contrast = float(gray.std())

    # Simple quality scoring – thresholds are configurable via env vars in future
    # For now we use hard‑coded thresholds that work for synthetic tests.
    blur_ok = blur_score > 100.0  # arbitrary; sharper images have higher variance
    brightness_ok = 50 <= brightness <= 200
    contrast_ok = contrast > 30.0

    quality_score = (int(blur_ok) + int(brightness_ok) + int(contrast_ok)) / 3.0
    quality_status = "good" if quality_score >= 0.66 else "poor"

    warnings = []
    if not blur_ok:
        warnings.append("Image may be blurry")
    if not brightness_ok:
        warnings.append("Brightness outside optimal range")
    if not contrast_ok:
        warnings.append("Low contrast detected")

    return {
        "resolution": {"width": width, "height": height},
        "blur_score": blur_score,
        "brightness": brightness,
        "contrast": contrast,
        "quality_score": quality_score,
        "quality_status": quality_status,
        "warnings": warnings,
    }
