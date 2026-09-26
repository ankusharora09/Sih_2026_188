"""Perspective correction utilities.

Given an image and a quadrilateral (list of four points), the
``correct_perspective`` function warps the image so that the quadrilateral
becomes a rectangle.
"""

from __future__ import annotations

import cv2
import numpy as np


def correct_perspective(image: np.ndarray, contour: list) -> dict:
    """Apply homography to obtain a top‑down view of the document.

    ``contour`` must be an iterable of four ``[x, y]`` points in the
    order returned by ``document_detector.detect_document``.

    Returns a dictionary with:
        - ``status``: ``"success"`` or ``"failed"``
        - ``corrected_image``: the warped ``np.ndarray`` (when successful)
        - ``metadata``: information about the transformation (original and
          corrected dimensions)
    """

    if not contour or len(contour) != 4:
        return {"status": "failed", "corrected_image": None, "metadata": {}}

    pts = np.array(contour, dtype="float32")
    (tl, tr, br, bl) = pts

    # Compute width and height of the new image
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1],
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(pts, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    metadata = {
        "original_dimensions": {"width": image.shape[1], "height": image.shape[0]},
        "corrected_dimensions": {"width": maxWidth, "height": maxHeight},
    }
    return {"status": "success", "corrected_image": warped, "metadata": metadata}
