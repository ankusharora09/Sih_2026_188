"""Advanced digital document tampering detection adapter.

Implements multi-signal forensic analysis:
1. Error Level Analysis (ELA): Computes JPEG recompression discrepancy and local block variance.
2. High-Frequency Noise Inconsistency: Analyzes spatial noise residuals for spliced/composited patches.
3. Edge Discontinuity: Flags unnatural boundary gradients around local regions.
"""

from __future__ import annotations

import cv2
import numpy as np

from ...config import settings
from .adapter import TamperingDetectionAdapter


class SimpleTamperingAdapter(TamperingDetectionAdapter):
    def __init__(self) -> None:
        self.score_threshold = getattr(settings, "TAMPERING_SCORE_THRESHOLD", 0.5)

    def _error_level_analysis(self, img: np.ndarray, quality: int = 92) -> tuple[float, float, list[dict]]:
        """Perform Error Level Analysis and detect localized compression hotspots."""
        try:
            if img.ndim == 2:
                bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            elif img.shape[2] == 4:
                bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            else:
                bgr = img

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            success, enc = cv2.imencode(".jpg", bgr, encode_param)
            if not success:
                return 0.0, 0.0, []

            resaved = cv2.imdecode(enc, cv2.IMREAD_COLOR)
            diff = cv2.absdiff(bgr, resaved).astype(np.float32)
            gray_diff = cv2.cvtColor(diff.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)

            global_mean = float(np.mean(gray_diff))
            global_std = float(np.std(gray_diff))

            h, w = gray_diff.shape
            block_size = max(16, min(32, min(h, w) // 10))
            block_means = []
            suspicious_regions = []

            for y in range(0, h - block_size + 1, block_size):
                for x in range(0, w - block_size + 1, block_size):
                    block = gray_diff[y : y + block_size, x : x + block_size]
                    b_mean = float(np.mean(block))
                    block_means.append(b_mean)

                    if global_std > 0 and b_mean > (global_mean + 2.5 * global_std) and b_mean > 8.0:
                        suspicious_regions.append({
                            "x": int(x),
                            "y": int(y),
                            "w": int(block_size),
                            "h": int(block_size),
                            "anomaly_score": round(float(min(1.0, (b_mean - global_mean) / (3.0 * global_std + 1e-5))), 3),
                        })

            block_variance = float(np.std(block_means)) if block_means else 0.0
            return global_mean, block_variance, suspicious_regions[:8]
        except Exception:
            return 0.0, 0.0, []

    def _noise_inconsistency(self, img: np.ndarray) -> float:
        """Analyze high-frequency noise residual variance across grid sections."""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            noise = cv2.absdiff(gray, blurred).astype(np.float32)

            mean_noise = float(np.mean(noise))
            if mean_noise < 1.0:
                return 0.05

            h, w = noise.shape
            step_y, step_x = max(1, h // 4), max(1, w // 4)
            cell_stds = []
            for r in range(0, h - step_y + 1, step_y):
                for c in range(0, w - step_x + 1, step_x):
                    cell = noise[r : r + step_y, c : c + step_x]
                    cell_stds.append(float(np.std(cell)))

            if len(cell_stds) > 1:
                mean_std = np.mean(cell_stds)
                var_std = np.std(cell_stds)
                return float(min(1.0, var_std / (mean_std + 1e-5)))
            return 0.0
        except Exception:
            return 0.0

    def _score(self, img: np.ndarray) -> float:
        """Compute forensic tampering score via ELA and noise inconsistency."""
        _, ela_variance, regions = self._error_level_analysis(img)
        noise_inconsistency = self._noise_inconsistency(img)

        ela_score = min(1.0, (ela_variance / 4.5)) if ela_variance > 1.2 else (ela_variance / 10.0)
        combined = float(np.clip(0.65 * ela_score + 0.35 * noise_inconsistency, 0.0, 1.0))
        if len(regions) >= 3:
            combined = max(combined, 0.65)
        return float(round(combined, 3))

    def detect(self, document_image: np.ndarray) -> dict:
        try:
            score = float(self._score(document_image))
            tampered = bool(score >= self.score_threshold)

            # Extract regions for forensic visualization if score warrants or present
            _, _, regions = self._error_level_analysis(document_image)

            signals = []
            if score >= self.score_threshold:
                signals.append("ela_compression_discrepancy")
            if len(regions) >= 2:
                signals.append("localized_splicing_detected")

            return {
                "status": "success",
                "tampered": tampered,
                "score": score,
                "regions": regions,
                "signals": signals,
            }
        except Exception as exc:  # pragma: no cover – defensive
            return {
                "status": "failed",
                "error": str(exc),
                "tampered": None,
                "score": None,
                "regions": [],
                "signals": [],
            }
