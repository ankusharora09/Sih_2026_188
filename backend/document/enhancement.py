"""Image enhancement utilities.

The ``enhance_image`` function applies a series of conservative
pre‑processing steps: conversion to grayscale (if needed), CLAHE for contrast
enhancement, and a light bilateral filter for denoising. The function returns
the processed ``np.ndarray``.
"""

from __future__ import annotations

import cv2
import numpy as np


def enhance_image(image: np.ndarray) -> np.ndarray:
    """Enhance an image for OCR.

    Steps:
    1. Convert to grayscale.
    2. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).
    3. Apply a bilateral filter to reduce noise while preserving edges.
    """

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
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    # Bilateral filter parameters chosen to be gentle.
    filtered = cv2.bilateralFilter(enhanced, d=5, sigmaColor=75, sigmaSpace=75)
    return filtered
