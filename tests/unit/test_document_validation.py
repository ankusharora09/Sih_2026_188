"""Unit tests for SIH Modules 1+2: document-type detection, type-specific
extraction, and rule-based validation (expired / format / plausibility)."""

import pytest

from backend.services.document_validation import (
    detect_document_type,
    extract_document_fields,
    validate_document,
)


PASSPORT_TEXT = """REPUBLIC OF INDIA
PASSPORT
Type P Country Code IND Passport No. Z1234567
Surname
SHARMA
Given Name(s)
RAHUL KUMAR
Nationality INDIAN
Sex Male
Date of Birth 14/03/1998
Place of Birth DELHI
Date of Issue 12/08/2021
Date of Expiry 11/08/2031
P<INDSHARMA<<RAHUL<KUMAR<<<<<<<<<<<<<<<<<<<<<<
Z1234567IND9803142M3108115<<<<<<<<<<<<<<02"""

VISA_TEXT = """GOVERNMENT OF INDIA
VISA
Visa No. 12345678
Visa Type: Employment Visa
Entry: Multiple
Stay Duration: 180 days
Date of Issue 01/06/2026
Valid Until 30/09/2026
Nationality: CHINESE"""

DL_TEXT = """TRANSPORT DEPARTMENT
DRIVING LICENCE
DL No. KA05 20190001234
Name: ANIL KUMAR
DOB: 07-11-2001
Blood Group: B+
Valid Till: 06/11/2041"""


class TestTypeDetection:
    def test_passport(self):
        assert detect_document_type(PASSPORT_TEXT)["document_type"] == "passport"

    def test_visa(self):
        assert detect_document_type(VISA_TEXT)["document_type"] == "visa"

    def test_dl(self):
        assert detect_document_type(DL_TEXT)["document_type"] == "driving_licence"

    def test_unknown(self):
        assert detect_document_type("some random receipt text")["document_type"] == "unknown"


class TestPassportExtraction:
    def test_passport_number(self):
        f = extract_document_fields(PASSPORT_TEXT)
        assert f["passport_number"] == "Z1234567"

    def test_nationality(self):
        assert extract_document_fields(PASSPORT_TEXT)["nationality"] == "Indian"

    def test_expiry(self):
        assert extract_document_fields(PASSPORT_TEXT)["date_of_expiry"] == "11/08/2031"

    def test_mrz_detected(self):
        assert extract_document_fields(PASSPORT_TEXT)["mrz_present"] is True

    def test_gender(self):
        assert extract_document_fields(PASSPORT_TEXT)["gender"] == "Male"


class TestVisaExtraction:
    def test_visa_number(self):
        assert extract_document_fields(VISA_TEXT)["visa_number"] == "12345678"

    def test_visa_type(self):
        assert extract_document_fields(VISA_TEXT)["visa_type"] == "Employment Visa"

    def test_stay_duration(self):
        assert extract_document_fields(VISA_TEXT)["stay_duration"].lower().startswith("180")


class TestValidation:
    def _checks(self, text):
        return {c["field"]: c for c in validate_document(text)["checks"]}

    def test_valid_passport_passes(self):
        res = validate_document(PASSPORT_TEXT)
        assert res["summary"]["verdict"] == "pass"
        assert res["summary"]["violations"] == 0

    def test_expired_document_flagged(self):
        text = PASSPORT_TEXT.replace("11/08/2031", "11/08/2019")
        checks = self._checks(text)
        assert checks["date_of_expiry"]["status"] == "expired"
        assert validate_document(text)["summary"]["verdict"] == "fail"

    def test_expiring_soon(self):
        from datetime import date, timedelta
        soon = (date.today() + timedelta(days=10)).strftime("%d/%m/%Y")
        text = PASSPORT_TEXT.replace("11/08/2031", soon)
        assert self._checks(text)["date_of_expiry"]["status"] == "expiring_soon"

    def test_invalid_passport_number_format(self):
        text = PASSPORT_TEXT.replace("Z1234567", "1234567")
        assert self._checks(text)["passport_number"]["status"] == "invalid_format"

    def test_implausible_dob(self):
        text = PASSPORT_TEXT.replace("14/03/1998", "14/03/2180")
        assert self._checks(text)["date_of_birth"]["status"] == "implausible"

    def test_mrz_missing_is_reported_not_fatal(self):
        text = "\n".join(l for l in PASSPORT_TEXT.splitlines() if not l.startswith(("P<", "Z1234567IND")))
        checks = self._checks(text)
        assert checks["mrz"]["status"] == "missing"
        assert validate_document(text)["summary"]["verdict"] == "incomplete"

    def test_garbage_text_never_crashes(self):
        res = validate_document("bleh 123 foo")
        assert res["summary"]["verdict"] in ("incomplete", "fail")

    def test_note_is_officer_framed(self):
        assert "automatic" in validate_document(PASSPORT_TEXT)["summary"]["note"]


# Verbatim PaddleOCR output from a live screening of a synthetic Aadhaar-style
# card — the case that exposed the false-MISSING bug.
NOISY_OCR_TEXT = """. a Elon Musk
~ oe Male
am 28/06/1971 = [Ere [mt]
i 789, Space ,
Colony ops j
4567 8901 2345
Q AT aan, At Wart
AADHAAR.
& Elon Musk
NE _ Male
28/06/1971
- > 789, Space
Colony"""


class TestNoisyRealOcr:
    """Fields present in noisy real OCR text must never be reported missing."""

    def _checks(self, text):
        return {c["field"]: c for c in validate_document(text)["checks"]}

    def test_name_found_in_noisy_text(self):
        f = extract_document_fields(NOISY_OCR_TEXT, fuzzy=True)
        assert f["full_name"] and f["full_name"].rstrip("?") == "Elon Musk"

    def test_dob_found_in_noisy_text(self):
        f = extract_document_fields(NOISY_OCR_TEXT, fuzzy=True)
        assert f["date_of_birth"] and f["date_of_birth"].startswith("28/06/1971")

    def test_noisy_fields_grade_low_confidence_not_missing(self):
        checks = self._checks(NOISY_OCR_TEXT)
        assert checks["full_name"]["status"] == "ok"
        assert checks["full_name"].get("low_confidence") is True
        assert checks["date_of_birth"]["status"] == "ok"
        assert checks["date_of_birth"].get("low_confidence") is True

    def test_noisy_summary_is_low_confidence_verdict(self):
        summary = validate_document(NOISY_OCR_TEXT)["summary"]
        assert summary["missing_fields"] == 0
        assert summary["low_confidence_fields"] >= 1
        assert summary["verdict"] == "low_confidence"

    def test_aadhaar_number_extracted(self):
        checks = self._checks(NOISY_OCR_TEXT)
        assert checks["aadhaar_number"]["status"] == "ok"
        assert checks["aadhaar_number"]["value"] == "4567 8901 2345"

    def test_aadhaar_never_reports_missing_expiry(self):
        """Aadhaar cards carry no expiry — it must not even be a check."""
        checks = self._checks(NOISY_OCR_TEXT)
        assert "date_of_expiry" not in checks

    def test_missing_field_detection_still_works(self):
        # A document with genuinely nothing extractable
        checks = self._checks("AADHAAR\nsome address text")
        assert checks["full_name"]["status"] == "missing"
        assert checks["date_of_birth"]["status"] == "missing"

    def test_genuinely_missing_name_stays_missing(self):
        text = PASSPORT_TEXT.replace("SHARMA\n", "").replace("RAHUL KUMAR\n", "")
        checks = self._checks(text)
        assert checks["full_name"]["status"] in ("missing", "implausible")
