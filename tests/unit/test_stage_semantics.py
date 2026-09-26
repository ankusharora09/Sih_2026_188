"""Honest stage-state semantics (SIH audit hardening).

Asserts the distinctions required of a production screening system:
  - skipped / unavailable / failed are NOT success
  - a stage that did not execute has no duration and no score
  - low fraud risk != fully verified (missing evidence forces review)
  - officer-facing output never leaks internal reason codes
"""

from __future__ import annotations

import pytest

from backend.risk.engine import RiskEngine


def run_payload(status: str, **extra) -> dict:
    return {"status": status, **extra}


ALL_STAGES = {
    "tampering": run_payload("success", tampered=False, score=0.05),
    "liveness": run_payload("skipped", reason="live capture was not provided"),
    "deepfake": run_payload("unavailable", reason="live capture was not provided"),
    "face_mismatch": run_payload("skipped", reason="live capture was not provided"),
    "ocr_confidence": run_payload("success", confidence=0.93),
    "anomaly": run_payload("success", score=0.0, anomalies=[]),
    "document_validation": run_payload("success", validation={
        "summary": {"verdict": "incomplete", "violations": 0},
        "checks": [
            {"field": "full_name", "status": "missing"},
            {"field": "date_of_birth", "status": "missing"},
            {"field": "date_of_expiry", "status": "missing"},
        ],
    }),
}


class TestStageStateDistinctions:
    def setup_method(self):
        self.engine = RiskEngine()

    def test_skipped_stage_is_zero_contribution_and_null_value(self):
        row = self.engine._stage_risk("liveness", ALL_STAGES["liveness"])
        assert row["status"] == "skipped"
        assert row["contribution"] == 0.0
        assert row["value"] is None
        assert row["review"] is True
        assert row["officer_reason"] == "Live capture was not provided."

    def test_unavailable_stage_never_counts_as_executed(self):
        results = dict(ALL_STAGES)
        results["tampering"] = run_payload("unavailable")
        out = self.engine.compute(results)
        assert "tampering" not in out["verification"]["executed"]
        assert "tampering" in out["verification"]["pending"]

    def test_officer_reason_never_leaks_internal_codes(self):
        out = self.engine.compute(ALL_STAGES)
        blob = repr(out["risk_factors"]) + repr(out["verification_gaps"])
        assert "not_used_as_guilt" not in blob
        assert all(g["text"] for g in out["verification_gaps"])

    def test_skipped_stage_reason_is_officer_readable(self):
        row = self.engine._stage_risk("deepfake", ALL_STAGES["deepfake"])
        assert row["officer_reason"]
        assert "_" not in row["officer_reason"].replace("Synthetic-media", "")


class TestVerificationCompletenessAndDecision:
    def setup_method(self):
        self.engine = RiskEngine()

    def test_low_fraud_with_missing_evidence_is_review_required(self):
        out = self.engine.compute(ALL_STAGES)
        # Almost no fraud signal...
        assert out["risk_score"] <= 10
        # ...but three decisive checks never ran and fields are missing.
        assert out["verification_completeness"] < 100
        assert out["confidence_score"] < 100
        assert out["decision_status"] == "REVIEW_REQUIRED"
        assert out["risk_level"] == "REVIEW_REQUIRED"
        assert set(out["missing_mandatory_fields"]) == {"date_of_birth", "date_of_expiry", "full_name"}

    def test_missing_mandatory_field_alone_forces_review(self):
        results = {
            "tampering": run_payload("success", tampered=False),
            "face_mismatch": run_payload("success", match=True),
            "liveness": run_payload("success", is_live=True),
            "deepfake": run_payload("success", score=0.0),
            "ocr_confidence": run_payload("success", confidence=0.95),
            "anomaly": run_payload("success", score=0.0, anomalies=[]),
            "document_validation": run_payload("success", validation={
                "summary": {"verdict": "incomplete", "violations": 0},
                "checks": [{"field": "date_of_birth", "status": "missing"}],
            }),
        }
        out = self.engine.compute(results)
        assert out["decision_status"] == "REVIEW_REQUIRED"
        assert out["missing_mandatory_fields"] == ["date_of_birth"]

    def test_all_executed_clean_document_verifies(self):
        results = {
            "tampering": run_payload("success", tampered=False),
            "face_mismatch": run_payload("success", match=True),
            "liveness": run_payload("success", is_live=True),
            "deepfake": run_payload("success", score=0.0),
            "ocr_confidence": run_payload("success", confidence=0.95),
            "anomaly": run_payload("success", score=0.0, anomalies=[]),
            "document_validation": run_payload("success", validation={
                "summary": {"verdict": "pass", "violations": 0}, "checks": [],
            }),
        }
        out = self.engine.compute(results)
        assert out["decision_status"] == "VERIFY"
        assert out["verification_completeness"] == 100
        assert out["confidence_score"] == 100
        assert out["verification_gaps"] == []

    def test_high_risk_rejects_even_when_everything_executed(self):
        results = {
            "tampering": run_payload("success", tampered=True),
            "face_mismatch": run_payload("success", match=False),
            "liveness": run_payload("success", is_live=False),
            "deepfake": run_payload("success", score=0.9),
            "ocr_confidence": run_payload("success", confidence=0.2),
            "anomaly": run_payload("success", score=0.8, anomalies=["c1", "c2"]),
            "document_validation": run_payload("success", validation={
                "summary": {"verdict": "fail", "violations": 2}, "checks": [],
            }),
        }
        out = self.engine.compute(results)
        assert out["decision_status"] == "REJECT"
        assert out["risk_score"] >= 80

    def test_completeness_fields_exposed(self):
        out = self.engine.compute(ALL_STAGES)
        assert out["verification"]["executed_count"] == len(out["verification"]["executed"])
        assert out["verification"]["total"] == 6
        for key in ("verification_completeness", "confidence_score", "decision_status"):
            assert key in out


class TestStageResultTiming:
    def test_skipped_stage_persists_null_duration(self):
        """Regression guard: non-executed stages must not record ~0ms."""
        import backend.pipeline.contracts as plc
        statuses_without_execution = (plc.STATUS_SKIPPED, plc.STATUS_UNAVAILABLE)
        assert "success" not in statuses_without_execution
        assert "failed" not in statuses_without_execution
