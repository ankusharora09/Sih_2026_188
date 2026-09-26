"""Document boundary detection utilities.

The ``detect_document`` function attempts to locate a quadrilateral that
represents the outer edge of a document in the given image. It returns a
dictionary with a ``status`` field (``"success"`` or ``"failed"``) and,
when successful, a ``contour`` key containing the four points in
clockwise order.
"""

from __future__ import annotations

import cv2
import numpy as np


def _order_quad(pts: np.ndarray) -> np.ndarray:
    # Order points: top‑left, top‑right, bottom‑right, bottom‑left
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def detect_document(image: np.ndarray) -> dict:
    """Detect the largest 4‑point contour approximating a document.

    Returns a dictionary:
        {
            "status": "success" | "failed",
            "contour": [[x, y], ...]  # 4 points in order, when successful
        }
    """

    # Convert to grayscale for processing
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

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    h_img, w_img = gray.shape[:2]
    img_area = float(h_img * w_img)

    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        pts = approx.reshape(4, 2)
        ordered = _order_quad(pts)

        # Sanity guards: a plausible document spans a substantial part of the
        # frame. Without them, Canny noise inside a portrait photo (e.g. the
        # picture-frame strip behind a head-and-shoulders crop) was accepted
        # as the "document" and perspective-corrected onto, destroying the
        # actual content for every later stage (OCR, face verification).
        quad_area = float(cv2.contourArea(ordered)) if cv2.contourArea(ordered) > 0 else 0.0
        if img_area <= 0 or (quad_area / img_area) < 0.15:
            continue
        width = float(np.linalg.norm(ordered[1] - ordered[0]))
        height = float(np.linalg.norm(ordered[3] - ordered[0]))
        if min(width, height) < 80:
            continue
        aspect = (width / height) if height > 0 else 0.0
        if not (0.35 <= aspect <= 2.6):
            continue

        return {"status": "success", "contour": ordered.tolist()}

    return {"status": "failed", "contour": []}
