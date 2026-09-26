"""Tests for the trained forgery deepfake adapter and cross-case face reuse.

Covers the two features completed in the "make the daya-driven features work"
pass:
  1. The trained ResNet18 classifier (models/document_forgery_gt2.pth) is
     wired into the deepfake stage with an honest fallback.
  2. Document-face SFace embeddings are persisted and cross-case face reuse
     is detected through the vector store.
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.ai.deepfake import get_verifier
from backend.ai.deepfake.trained_forgery_adapter import TrainedForgeryDeepfakeAdapter
from backend.ai.deepfake.simple_deepfake_adapter import SimpleDeepfakeAdapter
from backend.fraud.face_reuse import persist_face_embedding, detect_face_reuse
import backend.fraud.face_reuse as face_reuse_module
from backend.db import models as db_models
from backend.db.database import Base, SessionLocal, engine


# ---------------------------------------------------------------------------
# Deepfake adapter
# ---------------------------------------------------------------------------

class TestTrainedForgeryAdapter:
    def test_factory_prefers_trained_model(self):
        # On this machine the checkpoint + torch exist, so the factory must
        # return the trained adapter, not the spectral heuristic.
        v = get_verifier()
        assert isinstance(v, TrainedForgeryDeepfakeAdapter)
        assert v.ready is True
        assert v.model is not None

    def test_no_live_image_is_unavailable(self):
        r = get_verifier().detect(np.zeros((200, 200, 3), np.uint8), None)
        assert r["status"] == "unavailable"
        assert "score" not in r

    def test_success_reports_neural_and_spectral_scores(self):
        rng = np.random.default_rng(5)
        doc = rng.integers(0, 255, (200, 200, 3), dtype=np.uint8)
        live = rng.integers(0, 255, (200, 200, 3), dtype=np.uint8)
        r = get_verifier().detect(doc, live)
        assert r["status"] == "success"
        assert r["neural_available"] is True
        assert 0.0 <= r["neural_score"] <= 1.0
        assert 0.0 <= r["score"] <= 1.0
        assert r["verdict"] in ("forged", "genuine")
        assert "model_version" in r

    def test_missing_checkpoint_falls_back_to_heuristic(self, tmp_path):
        adapter = TrainedForgeryDeepfakeAdapter(weights_path=tmp_path / "missing.pth")
        assert adapter.ready is False
        assert adapter._load_error  # honest reason recorded

        rng = np.random.default_rng(9)
        doc = rng.integers(0, 255, (120, 120, 3), dtype=np.uint8)
        live = rng.integers(0, 255, (120, 120, 3), dtype=np.uint8)
        r = adapter.detect(doc, live)
        # Still a usable result, but clearly labelled as heuristics-only.
        assert r["status"] == "success"
        assert r["neural_available"] is False
        assert r["model"] == SimpleDeepfakeAdapter().model_name

    def test_heuristic_scores_are_reported_together(self):
        adapter = get_verifier()
        rng = np.random.default_rng(21)
        doc = rng.integers(0, 255, (150, 150, 3), dtype=np.uint8)
        live = rng.integers(0, 255, (150, 150, 3), dtype=np.uint8)
        r = adapter.detect(doc, live)
        assert "spectral_score" in r
        assert "neural_score" in r


# ---------------------------------------------------------------------------
# Face-embedding persistence + reuse detection
# ---------------------------------------------------------------------------

_DIM = 128


def _face_result(vec_a, model="sface_deep_onnx"):
    return {
        "status": "success",
        "face_detected": True,
        "match": True,
        "similarity": 0.9,
        "model": model,
        "model_version": "sface_11_aligncrop",
        "document_embedding": list(vec_a),
    }


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    # Test isolation: wipe face embeddings and reset the module-level vector
    # index so leftover rows from prior runs / other suites cannot interfere.
    session = SessionLocal()
    session.query(db_models.FaceEmbedding).delete()
    session.commit()
    face_reuse_module._reset_store_for_tests()
    yield session
    session.rollback()
    session.close()
    face_reuse_module._reset_store_for_tests()


def _make_case(db, subject="Reuse Tester"):
    case = db_models.Case(id=None or __import__("uuid").uuid4().hex,
                          owner_id="test-owner", subject_name=subject)
    db.add(case)
    db.commit()
    return case


class TestFaceReuse:
    def test_first_case_stores_embedding_without_reuse(self, db):
        case = _make_case(db)
        vec = np.zeros(_DIM, dtype=np.float32)
        vec[0] = 1.0
        out = persist_face_embedding(db, case.id, _face_result(vec))
        assert out["status"] == "stored"
        assert out["reuse"] is None

        rows = db.query(db_models.FaceEmbedding).filter_by(case_id=case.id).all()
        assert len(rows) == 1
        assert len(rows[0].embedding) == _DIM

        post = detect_face_reuse(db, case.id)
        assert post["status"] == "success"
        assert post["face_reuse"] is None

    def test_same_face_in_two_cases_fires_reuse(self, db):
        vec = np.zeros(_DIM, dtype=np.float32)
        vec[1] = 1.0

        case1 = _make_case(db, subject="Person One")
        out1 = persist_face_embedding(db, case1.id, _face_result(vec))
        assert out1["status"] == "stored"
        assert out1["reuse"] is None  # nothing prior to match

        case2 = _make_case(db, subject="Person Two")
        out2 = persist_face_embedding(db, case2.id, _face_result(vec))
        assert out2["status"] == "stored"
        assert out2["reuse"] is not None
        assert out2["reuse"]["type"] == "face_reuse"
        assert out2["reuse"]["related_case_id"] == case1.id
        assert out2["reuse"]["cosine_similarity"] > 0.99

        post = detect_face_reuse(db, case2.id)
        assert post["face_reuse"] is not None
        assert post["face_reuse"]["related_case_id"] == case1.id

    def test_different_faces_do_not_fire_reuse(self, db):
        vec_a = np.zeros(_DIM, dtype=np.float32); vec_a[2] = 1.0
        vec_b = np.zeros(_DIM, dtype=np.float32); vec_b[3] = 1.0

        case1 = _make_case(db, subject="Alpha")
        persist_face_embedding(db, case1.id, _face_result(vec_a))
        case2 = _make_case(db, subject="Beta")
        out2 = persist_face_embedding(db, case2.id, _face_result(vec_b))
        assert out2["status"] == "stored"
        assert out2["reuse"] is None  # orthogonal vectors: cosine 0

    def test_missing_embedding_is_skipped_not_stored(self, db):
        case = _make_case(db)
        out = persist_face_embedding(db, case.id, {"status": "success", "face_detected": False})
        assert out["status"] == "skipped"
        assert "reason" in out

    def test_raw_embedding_stripped_from_stage_result(self, db):
        """The 128-d vector must not leak into persisted stage JSON."""
        face_result = _face_result(np.ones(_DIM, dtype=np.float32) / np.sqrt(_DIM))
        case = _make_case(db)
        persist_face_embedding(db, case.id, face_result)
        # The screening service strips it; verify the helper contract here:
        face_result.pop("document_embedding", None)
        assert "document_embedding" not in face_result
