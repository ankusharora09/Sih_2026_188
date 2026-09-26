"""Adversarial and edge-case tests: presentation attacks, degenerate inputs,
calibration properties, and tampering signal sanity (Phases 3, 4, 6, 18)."""

import numpy as np
import pytest

from backend.ai.face import get_verifier
from backend.ai.face.haar_adapter import _FALLBACK_MATCH_THRESHOLD
from backend.ai.liveness import get_verifier as get_liveness_verifier
from backend.ai.tampering import get_verifier as get_tamper_verifier
from backend.ai.deepfake import get_verifier as get_deepfake_verifier
from backend.ai.ocr import service as ocr_service


@pytest.fixture
def verifier():
    return get_verifier()


class TestDegenerateInputs:
    """Phase 18 items 3-5, 12: garbage must never become a confident match."""

    def test_noise_never_matches_itself(self, verifier):
        rng = np.random.default_rng(42)
        noise = rng.integers(0, 255, (300, 300, 3), dtype=np.uint8)
        r = verifier.verify(noise, noise)
        assert r["status"] == "success"
        assert r["match"] is None, "textured noise must not produce a face match"
        assert r["similarity"] is None

    def test_flat_image_no_face(self, verifier):
        blank = np.full((300, 300, 3), 128, dtype=np.uint8)
        r = verifier.verify(blank, blank)
        assert r["match"] is None
        assert r["faces_count"] == 0

    def test_tiny_image_no_face(self, verifier):
        tiny = np.full((20, 20, 3), 200, dtype=np.uint8)
        r = verifier.verify(tiny, tiny)
        assert r["match"] is None

    def test_no_face_reports_uncertainty(self, verifier):
        blank = np.full((300, 300, 3), 128, dtype=np.uint8)
        r = verifier.verify(blank, blank)
        assert r["uncertainty"] == "no_face"
        assert "uncertainty" in r and "model_version" in r


class TestCalibration:
    """Phase 3: similarity math must be monotone and respect the threshold."""

    def test_calibration_monotone_and_bounded(self, verifier):
        prev = -1.0
        for cos in [0.0, 0.1, 0.2, 0.30, 0.362, 0.363, 0.45, 0.6, 0.9]:
            match, sim = verifier._calibrate(cos)
            assert 0.05 <= sim <= 0.99
            if match:
                assert sim >= verifier.threshold
            else:
                assert sim < verifier.threshold
            assert sim >= prev - 1e-9, "calibration must be monotone in raw cosine"
            prev = sim

    def test_boundary_exactly_at_official_threshold_matches(self, verifier):
        match, sim = verifier._calibrate(verifier.sface_cosine_threshold)
        assert match is True
        assert sim >= verifier.threshold

    def test_just_below_threshold_is_reject_with_gradation(self, verifier):
        match, sim = verifier._calibrate(0.30)
        assert match is False
        assert 0.3 < sim < verifier.threshold  # gradation preserved, not clamped


class TestFallbackPath:
    """The uncalibrated gradient fallback must use its own stricter gate."""

    def test_fallback_threshold_stricter_than_deep(self):
        assert _FALLBACK_MATCH_THRESHOLD > get_verifier().threshold

    def test_fallback_match_uses_fallback_threshold(self, verifier):
        roi = np.ones((64, 64), dtype=np.uint8)
        emb = np.ones(4096) / np.linalg.norm(np.ones(4096))
        verifier._detect_faces = lambda img: [roi]          # noqa: SLF001 - deliberate
        verifier._embed = lambda r: emb                     # noqa: SLF001 - deliberate
        r = verifier.verify(np.zeros((100, 100, 3)), np.zeros((100, 100, 3)))
        assert r["match"] is True
        assert r["similarity"] == pytest.approx(1.0)
        assert r["uncertainty"] == "uncalibrated_fallback"

    def test_fallback_below_own_threshold_no_match(self, verifier):
        roi_a = np.ones((64, 64), dtype=np.uint8)
        roi_b = np.full((64, 64), 2, dtype=np.uint8)
        half = np.zeros(4096); half[:2048] = 1.0
        verifier._detect_faces = lambda img: [roi_a] if img.shape[0] == 100 else [roi_b]  # noqa: SLF001
        verifier._embed = lambda r: (half if r is roi_a else -half)  # noqa: SLF001
        r = verifier.verify(np.zeros((100, 100, 3)), np.zeros((200, 200, 3)))
        assert r["match"] is False


class TestLivenessPresentationAttacks:
    """Phase 4: the sharpness/entropy heuristic is not a real liveness model.

    These tests pin what it CAN honestly detect: its own signals and honest
    status reporting. Printed-photo/replay detection is NOT claimed.
    """

    def test_flat_image_not_live(self):
        r = get_liveness_verifier().detect(np.full((200, 200, 3), 128, dtype=np.uint8))
        assert r["status"] == "success"
        assert r["is_live"] is False  # zero sharpness and low entropy

    def test_detailed_texture_scores_live(self):
        rng = np.random.default_rng(7)
        textured = rng.integers(0, 255, (200, 200, 3), dtype=np.uint8)
        r = get_liveness_verifier().detect(textured)
        assert r["is_live"] is True  # high sharpness + high entropy
        assert r["sharpness"] > 0 and r["entropy"] > 0

    def test_thresholds_reported(self):
        r = get_liveness_verifier().detect(np.zeros((100, 100, 3), dtype=np.uint8))
        assert set(r["thresholds"]) == {"sharpness", "entropy"}


class TestTamperingSignals:
    """Phase 6: signals and regions must be present and honest."""

    def test_clean_flat_document_not_tampered(self):
        r = get_tamper_verifier().detect(np.full((400, 400, 3), 235, dtype=np.uint8))
        assert r["status"] == "success"
        assert r["tampered"] is False
        assert r["signals"] == []

    def test_result_contains_localized_regions_field(self):
        rng = np.random.default_rng(3)
        img = rng.integers(0, 255, (400, 400, 3), dtype=np.uint8)
        r = get_tamper_verifier().detect(img)
        assert "regions" in r and isinstance(r["regions"], list)
        for region in r["regions"]:
            assert {"x", "y", "w", "h", "anomaly_score"} <= set(region)


class TestDeepfakeHonesty:
    """Phase 4: no live capture -> honest 'unavailable', never a fake verdict."""

    def test_no_live_image_is_unavailable(self):
        doc = np.zeros((200, 200, 3), dtype=np.uint8)
        r = get_deepfake_verifier().detect(doc, None)
        assert r["status"] == "unavailable"
        assert "score" not in r

    def test_success_shape(self):
        rng = np.random.default_rng(11)
        doc = rng.integers(0, 255, (200, 200, 3), dtype=np.uint8)
        live = rng.integers(0, 255, (200, 200, 3), dtype=np.uint8)
        r = get_deepfake_verifier().detect(doc, live)
        assert r["status"] == "success"
        assert 0.0 <= r["score"] <= 1.0
        assert "indicators" in r


class TestOCREngineCaching:
    """Phase 17: engines must be constructed once, not per request."""

    def test_tesseract_engine_cached(self, monkeypatch):
        calls = {"n": 0}
        real_init = ocr_service.TesseractEngine.__init__

        def counting_init(self):
            calls["n"] += 1
            real_init(self)

        monkeypatch.setattr(ocr_service.TesseractEngine, "__init__", counting_init)
        monkeypatch.setattr(ocr_service, "_tesseract_engine", None)
        import numpy as np
        img = np.full((100, 300, 3), 255, dtype=np.uint8)
        ocr_service.perform_ocr(img)
        ocr_service.perform_ocr(img)
        assert calls["n"] == 1
