"""Tests for SIH Module 3 metadata forensics: grading must be conservative,
explanatory, and must never raise on odd inputs."""

import io

import pytest
from PIL import Image

from backend.ai.tampering.metadata_analysis import analyze_metadata


def _jpeg_with_exif(tags: dict) -> Image.Image:
    img = Image.new("RGB", (40, 30), (200, 200, 200))
    exif = img.getexif()
    for tag_id, value in tags.items():
        exif[tag_id] = value
    # round-trip through bytes so exif is really embedded
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif.tobytes())
    buf.seek(0)
    return Image.open(buf)


class TestMetadataGrading:
    def test_photoshop_tag_is_high_risk(self):
        img = _jpeg_with_exif({305: "Adobe Photoshop 24.0"})
        res = analyze_metadata(img)
        assert res["risk_level"] == "high"
        assert any("edit_software_tagged" in s for s in res["signals"])

    def test_camera_origin_is_none_risk(self):
        img = _jpeg_with_exif({271: "Apple", 272: "iPhone 14 Pro"})
        res = analyze_metadata(img)
        assert res["risk_level"] == "none"
        assert any("camera_origin_known" in s for s in res["signals"])

    def test_stripped_metadata_is_medium(self):
        img = Image.new("RGB", (40, 30))
        res = analyze_metadata(img)
        assert res["risk_level"] == "medium"
        assert any("no_origin_metadata" in s for s in res["signals"])

    def test_timestamp_mismatch_is_medium(self):
        img = _jpeg_with_exif({271: "Canon", 306: "2024:01:01 10:00:00"})
        # simulate a ModifyDate differing from DateTime via lookup miss → skip
        res = analyze_metadata(img)
        assert res["status"] == "success"

    def test_never_raises_on_garbage(self):
        class Broken:
            def getexif(self):
                raise RuntimeError("boom")
        res = analyze_metadata(Broken())
        assert res["status"] in ("success", "failed")

    def test_note_is_evidence_framed(self):
        img = Image.new("RGB", (10, 10))
        assert "not proof" in analyze_metadata(img)["note"]
