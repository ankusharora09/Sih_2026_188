







"""Simple liveness detection based on image sharpness and entropy.

The detector computes:
- Sharpness as the variance of the Laplacian (higher = sharper).
- Entropy of the grayscale histogram (higher = more texture/detail).
It compares these metrics against configurable thresholds from ``backend.config.settings``.
If both metrics exceed their thresholds, the image is considered live.
"""

from __future__ import annotations

import cv2
import numpy as np

from ...config import settings
from .adapter import LivenessDetectionAdapter


class SimpleLivenessAdapter(LivenessDetectionAdapter):
    def __init__(self) -> None:
        self.sharpness_threshold = settings.LIVENESS_SHARPNESS_THRESHOLD
        self.entropy_threshold = settings.LIVENESS_ENTROPY_THRESHOLD

    def _to_gray(self, img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 2:
            return img
        if len(img.shape) == 3 and img.shape[2] == 4:
            return cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        if len(img.shape) == 3 and img.shape[2] == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img

    def _sharpness(self, img: np.ndarray) -> float:
        gray = self._to_gray(img)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        return float(lap.var())

    def _entropy(self, img: np.ndarray) -> float:
        gray = self._to_gray(img)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.ravel()
        prob = hist / np.sum(hist)
        prob = prob[prob > 0]
        return float(-np.sum(prob * np.log2(prob)))

    def detect(self, live_image: np.ndarray) -> dict:
        try:
            sharpness = self._sharpness(live_image)
            entropy = self._entropy(live_image)
            is_live = sharpness >= self.sharpness_threshold and entropy >= self.entropy_threshold
            return {
                "status": "success",
                "is_live": is_live,
                "sharpness": sharpness,
                "entropy": entropy,
                "thresholds": {
                    "sharpness": self.sharpness_threshold,
                    "entropy": self.entropy_threshold,
                },
            }
        except Exception as exc:  # pragma: no cover – defensive
            return {
                "status": "failed",
                "error": str(exc),
                "is_live": False,
                "sharpness": None,
                "entropy": None,
                "thresholds": {
                    "sharpness": self.sharpness_threshold,
                    "entropy": self.entropy_threshold,
                },
            }
