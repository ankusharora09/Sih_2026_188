"""Rotation and deskew utilities.

``detect_and_correct_rotation`` attempts to estimate the dominant rotation of a
document and rotate it to upright orientation. For small angles it applies a
linear rotation; for 90/180/270 degree cases it uses ``cv2.rotate``.
"""

from __future__ import annotations

import cv2
import numpy as np


def _angle_of_contour(contour: np.ndarray) -> float:
    # Fit a minimum area rectangle and return its angle.
    rect = cv2.minAreaRect(contour)
    angle = rect[-1]
    # OpenCV returns angles in the range [-90, 0); adjust to natural range
    if angle < -45:
        angle = 90 + angle
    return angle


def detect_and_correct_rotation(image: np.ndarray, contour: list | None = None) -> dict:
    """Detect rotation from the document contour (if provided) and rotate.

    Returns a dictionary with ``status`` (``"success"`` or ``"failed"``),
    ``rotated_image`` (the corrected ``np.ndarray``) and ``metadata`` containing
    the estimated angle.
    """

    if contour:
        pts = np.array(contour, dtype="float32")
        angle = _angle_of_contour(pts)
        if abs(angle) < 1.0 or abs(angle - 90) < 1.0:
            angle = 0.0
    else:
        # Fallback: estimate skew from consistent horizontal/vertical text lines
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif len(image.shape) == 4:
            bgr = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 100)
        angle = 0.0
        if lines is not None and len(lines) >= 10:
            deviations = []
            for line in lines:
                theta = line[0][1] * 180.0 / np.pi
                dev_h = theta - 90.0
                if abs(dev_h) <= 15.0:
                    deviations.append(dev_h)
                elif theta <= 15.0:
                    deviations.append(theta)
                elif theta >= 165.0:
                    deviations.append(theta - 180.0)
            if len(deviations) >= 8 and np.std(deviations) < 1.5:
                median_dev = float(np.median(deviations))
                if abs(median_dev) >= 1.0:
                    angle = median_dev

    # If angle is negligible, do not warp
    if abs(angle) < 1.0:
        return {"status": "success", "rotated_image": image, "metadata": {"angle": 0.0, "snapped": 0}}

    # Normalize angle to nearest multiple of 90 if confidence is high
    snapped = round(angle / 90) * 90
    if abs(angle - snapped) <= 5:
        # Use cv2.rotate for 90/180/270 multiples
        if snapped % 360 == 90:
            rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif snapped % 360 == 180:
            rotated = cv2.rotate(image, cv2.ROTATE_180)
        elif snapped % 360 == 270:
            rotated = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            rotated = image
        return {"status": "success", "rotated_image": rotated, "metadata": {"angle": float(angle), "snapped": snapped}}
    else:
        # Apply a small corrective rotation using the rotation matrix
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return {"status": "success", "rotated_image": rotated, "metadata": {"angle": float(angle), "snapped": None}}
