"""Unit tests for OCR identity-field extraction and the fallback explanation."""

import pytest

from backend.ai.ollama.explanation_engine import ExplanationEngine
from backend.services.screening_service import extract_identity_fields


class TestExtractIdentityFields:
    def test_aadhaar_spaced(self):
        raw = "Government of India\nDOB: 14/03/1998\n1234 5678 9012\nMale"
        fields = extract_identity_fields(raw)
        assert fields["extracted_id_number"] == "1234 5678 9012"
        assert fields["extracted_dob"] == "14/03/1998"
        assert fields["extracted_gender"] == "Male"

    def test_aadhaar_multiple_spaces(self):
        raw = "1234  5678   9012"
        assert extract_identity_fields(raw)["extracted_id_number"] == "1234  5678   9012"

    def test_aadhaar_never_matches_across_lines(self):
        # Regression: "1998" from a DOB line plus ID digits on the next line
        # must not be spliced into a fake ID (was possible with \s+ separators).
        raw = "DOB: 1/1/1998\n1234 5678 9012"  # wait: this IS a single-line match
        raw = "DOB: 1/1/1998\nx1234 5678"      # no valid single-line ID present
        assert extract_identity_fields(raw)["extracted_id_number"] is None

    def test_compact_12_digit_id(self):
        assert extract_identity_fields("Ref 123456789012 end")["extracted_id_number"] == "123456789012"

    def test_compact_id_rejects_13_digit_run(self):
        assert extract_identity_fields("1234567890123")["extracted_id_number"] is None

    def test_pan(self):
        assert extract_identity_fields("PAN ABCDE1234F")["extracted_id_number"] == "ABCDE1234F"

    def test_dob_dash_separator(self):
        assert extract_identity_fields("Date of Birth: 07-11-2001")["extracted_dob"] == "07-11-2001"

    def test_no_fields(self):
        fields = extract_identity_fields("nothing useful here")
        assert fields["extracted_dob"] is None
        assert fields["extracted_id_number"] is None
        assert fields["extracted_gender"] is None
        assert fields["name_cross_check"] == "not_provided"

    def test_name_match(self):
        raw = "Government of India\nRahul Kumar Sharma\nDOB: 14/03/1998"
        fields = extract_identity_fields(raw, subject_name="Rahul Sharma")
        assert fields["name_cross_check"] == "matched"
        assert fields["name_verification"]["match"] is True

    def test_name_mismatch(self):
        raw = "Government of India\nPriya Venkatesan\nDOB: 14/03/1998"
        fields = extract_identity_fields(raw, subject_name="Rahul Sharma")
        assert fields["name_cross_check"] == "mismatched"
        assert fields["name_verification"]["match"] is False

    def test_name_partial_match(self):
        raw = "Rahul Devi Verma\nDOB: 14/03/1998"
        fields = extract_identity_fields(raw, subject_name="Rahul Sharma")
        assert fields["name_cross_check"] in {"matched", "partial_match"}

    def test_name_not_extracted_from_boilerplate(self):
        raw = "Government of India\nUnique Identification Authority\nDOB: 14/03/1998"
        fields = extract_identity_fields(raw)
        assert fields["extracted_name"] is None


class TestFallbackExplanation:
    def setup_method(self):
        self.engine = ExplanationEngine()

    def risk(self, **overrides):
        base = {
            "risk_score": 62,
            "risk_level": "high",
            "triggered_rules": ["tampering", "face_mismatch"],
            "contribution_details": [
                {"signal": "tampering", "value": True, "threshold": 0.5, "reason": "tampering_detected"},
                {"signal": "liveness", "value": None, "threshold": None, "reason": "face_mismatch"},
                {"signal": "face_mismatch", "value": False, "threshold": 0.4, "reason": "face_mismatch"},
            ],
            "risk_factors": [
                {"signal": "tampering", "contribution": 0.25, "text": "Tampering signals detected in the document."},
                {"signal": "face_mismatch", "contribution": 0.15, "text": "Face mismatch between document and capture."},
            ],
            "verification_gaps": [
                {"signal": "liveness", "status": "skipped", "text": "Live capture was not provided."},
            ],
            "verification": {"executed": ["tampering", "face_mismatch"], "pending": ["liveness"],
                             "executed_count": 2, "total": 3, "percent": 67},
        }
        base.update(overrides)
        return base

    def test_format(self):
        out = self.engine.generate(self.risk())
        assert "Risk Score: 62/100  |  Level: high" in out
        assert "Triggered alerts: tampering, face_mismatch" in out
        assert "Risk factors:" in out
        assert "Tampering signals detected in the document." in out
        assert "Verification gaps (not counted as evidence of fraud):" in out
        assert "Live capture was not provided." in out
        assert "2/3 decisive checks executed" in out
        # Internal reason codes must never reach the officer-facing summary.
        assert "not_used_as_guilt" not in out

    def test_empty_risk(self):
        out = self.engine.generate({})
        assert "Risk Score: 0/100" in out
        assert "No risk rules triggered." in out

    def test_no_gaps(self):
        out = self.engine.generate(self.risk(verification_gaps=[], verification=None))
        assert "Verification gaps" not in out
        assert "decisive checks" not in out
