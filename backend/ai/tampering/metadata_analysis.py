"""Image metadata forensics for the tampering stage (SIH Module 3).

Reads EXIF/metadata from the original upload when available and reports
edit-software traces, missing-metadata anomalies, and timestamp inconsistencies.
Metadata is *evidence*, never proof: a stripped photo is suspicious but common
(messengers strip EXIF), so findings are graded and explanatory.
"""

from __future__ import annotations

from typing import Any

# Software markers commonly seen on edited images
_EDIT_SOFTWARE = [
    "photoshop", "gimp", "lightroom", "snapseed", "picsart", "canva",
    "pixelmator", "affinity", "paint.net", "paintshop", "apture", "luminar",
]
_CAMERA_MAKES = ["canon", "nikon", "sony", "fujifilm", "panasonic", "olympus",
                 "apple", "samsung", "google", "xiaomi", "oneplus", "oppo", "vivo", "motorola"]


def _exif_dict(img) -> dict[str, Any]:
    """Best-effort EXIF extraction from a PIL Image; never raises."""
    try:
        exif = img.getexif()
        out: dict[str, Any] = {}
        for k, v in exif.items():
            try:
                out[str(k)] = v if isinstance(v, (str, int, float)) else str(v)
            except Exception:
                continue
        return out
    except Exception:
        return {}


def _lookup(exif: dict[str, Any], *names: str) -> str | None:
    low = {k.lower(): v for k, v in exif.items()}
    for n in names:
        if n in low:
            return str(low[n])
    return None


def analyze_metadata(img, source_path: str | None = None) -> dict[str, Any]:
    """Analyze image metadata for manipulation indicators.

    Returns a graded result:
      risk_level: none | low | medium | high
      signals:    list of human-readable findings
    """
    signals: list[str] = []
    exif = _exif_dict(img)

    software = _lookup(exif, "software", "305".__str__())  # 305 = Software tag
    make = _lookup(exif, "make", "271".__str__())          # 271 = Make
    model = _lookup(exif, "model", "272".__str__())        # 272 = Model
    datetime_tag = _lookup(exif, "datetime", "306".__str__())
    modify = _lookup(exif, "modifydate")

    software_low = (software or "").lower()
    editor = next((s for s in _EDIT_SOFTWARE if s in software_low), None)
    if editor:
        signals.append(f"edit_software_tagged: image metadata names editor '{software}'")
    elif "camera" in software_low or "camera" in (model or "").lower():
        signals.append(f"camera_firmware_tag: '{software}' (benign)")

    camera_origin = bool(make) or bool(model)
    if not camera_origin and not software:
        signals.append("no_origin_metadata: no camera make/model and no software tag present")

    if camera_origin:
        make_low = (make or "").lower()
        known = any(m in make_low for m in _CAMERA_MAKES)
        signals.append(("camera_origin_known: " if known else "camera_origin_unrecognised: ")
                       + f"{make or '?'} {model or ''}".strip())

    if datetime_tag and modify and datetime_tag != modify:
        signals.append(f"timestamp_mismatch: captured '{datetime_tag}' vs modified '{modify}'")

    # file-level fallback: read the stored bytes directly if PIL had no EXIF
    if not exif and source_path:
        try:
            from PIL import Image
            from PIL.ExifTags import Tags
            with Image.open(source_path) as im2:
                exif2 = im2.getexif()
                if exif2:
                    software2 = exif2.get(305)
                    if software2 and any(s in str(software2).lower() for s in _EDIT_SOFTWARE):
                        signals.append(f"edit_software_tagged: '{software2}'")
                    make2 = exif2.get(271)
                    model2 = exif2.get(272)
                    if make2 or model2:
                        signals.append(f"camera_origin_known: {make2 or '?'} {model2 or ''}".rstrip())
                        camera_origin = True
                    if not signals:
                        signals.append("metadata_present_but_uninformative")
        except Exception:
            pass

    # grade
    if editor:
        risk = "high"
    elif not camera_origin and not software:
        risk = "medium"   # fully stripped metadata
    elif any(s.startswith("timestamp_mismatch") for s in signals):
        risk = "medium"
    elif any(s.startswith("camera_origin_unrecognised") for s in signals):
        risk = "low"
    else:
        risk = "none"

    return {
        "status": "success",
        "risk_level": risk,
        "signals": signals,
        "has_exif": bool(exif),
        "software": software,
        "camera_make": make,
        "camera_model": model,
        "note": "Metadata findings are corroborating evidence, not proof of forgery. Messaging apps commonly strip EXIF.",
    }
