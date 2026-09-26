"""Document-type detection, type-specific field extraction and validation.

SIH 26188 Module 1 (OCR extraction) + Module 2 (document validation).

This module is pure and deterministic — no ML models. It:
  1. classifies the OCR text into a document type (passport / visa / national id /
     driving licence / pan / aadhaar / unknown) from keyword evidence,
  2. extracts the fields the SIH problem statement asks for per type,
  3. applies official-standard validation rules and returns per-field verdicts.

Validation is deliberately conservative: a failed rule is evidence for the
officer, never an automatic accusation.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Type detection
# ---------------------------------------------------------------------------

_TYPE_KEYWORDS: dict[str, list[str]] = {
    "passport": [r"passport", r"republic of india", r"ministry of external affairs"],
    "visa": [r"\bvisa\b", r"visa type", r"entry\s+(type|valid)", r"stay duration"],
    "driving_licence": [r"driving licen[cs]e", r"\bdl[-\s]?no\b", r"transport department"],
    "pan": [r"income tax department", r"\bpermanent account number\b", r"\bpan\b"],
    "aadhaar": [r"aadhaar", r"aadhahar", r"unique identification", r"uidai"],
    "voter_id": [r"election commission", r"epic no", r"elector"],
}

_TYPE_WEIGHTS = {
    "passport": 3.0,   # a literal "passport" mention is nearly decisive
    "visa": 2.0,
    "driving_licence": 2.5,
    "pan": 2.5,
    "aadhaar": 2.0,
    "voter_id": 2.5,
}


def detect_document_type(raw_text: str) -> dict[str, Any]:
    """Classify the document type from OCR text with weighted keyword evidence."""
    scores: dict[str, float] = {}
    matched: dict[str, list[str]] = {}
    low = (raw_text or "").lower()
    for dtype, patterns in _TYPE_KEYWORDS.items():
        score, hits = 0.0, []
        for pat in patterns:
            for m in re.finditer(pat, low):
                score += _TYPE_WEIGHTS[dtype]
                hits.append(m.group(0))
        if score > 0:
            scores[dtype] = score
            matched[dtype] = sorted(set(hits))
    if not scores:
        return {"document_type": "unknown", "confidence": 0.0, "evidence": {}}
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    return {
        "document_type": best,
        "confidence": round(scores[best] / total, 2),
        "evidence": matched,
    }


# ---------------------------------------------------------------------------
# Type-specific extraction
# ---------------------------------------------------------------------------

_NAME_STOP = re.compile(
    r"\b(government|ministry|republic|authority|department|india|union|secretary|"
    r"passport|visa|licen[cs]e|income tax|election|uidai|see|above|overleaf|"
    r"identification|aadhaar|colony|space|male|female|nationality|sex|date|"
    r"address|dob)\b", re.I)

_DATE_RE = re.compile(r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})\b")
_TITLE_CASE_NAME = re.compile(r"\b([A-Z][a-z]{1,15})(\s+[A-Z][a-z]{1,15}){1,3}\b")

# Passport number: letter + 7 digits (India) or 2 letters + 6 digits (many others)
_PASSPORT_NO_RE = re.compile(r"\b([A-Z][0-9]{7}|[A-Z]{2}[0-9]{6})\b")
# Visa number: typically 8+ digits
_VISA_NO_RE = re.compile(r"\b([0-9]{8,12})\b")
# Indian driving licence: NN letter-digits-letter-digits e.g. KA05 20190001234
_DL_RE = re.compile(r"\b([A-Z]{2}[-\s]?\d{1,2}[-\s]?(?:19|20)\d{2}\d{6,8})\b")
# Nationality field
_NATIONALITY_RE = re.compile(r"nationality[:\s]+([A-Za-z ]{3,24})", re.I)
_GENDER_RE = re.compile(r"\b(sex|gender)[:\s/]*\b(male|female|m|f|transgender)\b", re.I)
# MRZ line: two lines of >30 chars from the TD1/TD3 charset
_MRZ_LINE_RE = re.compile(r"^[A-Z0-9<]{30,}$")


def _find_lines(raw_text: str) -> list[str]:
    return [l.strip() for l in (raw_text or "").splitlines() if l.strip()]


def _mrz_lines(raw_text: str) -> list[str]:
    return [l for l in _find_lines(raw_text) if _MRZ_LINE_RE.match(l.replace(" ", "").upper())]


def _labelled_date(lines: list[str], labels: list[str]) -> str | None:
    """Date that follows a label, e.g. 'Date of Expiry: 12/08/2031'."""
    for i, line in enumerate(lines):
        for lab in labels:
            if re.search(lab, line, re.I):
                # date on the same line, else the next line
                m = _DATE_RE.search(line)
                if m:
                    return m.group(1)
                for j in (i + 1, i + 2):
                    if j < len(lines):
                        m = _DATE_RE.search(lines[j])
                        if m:
                            return m.group(1)
    return None


def _labelled_value(lines: list[str], labels: list[str], pattern: re.Pattern) -> str | None:
    for line in lines:
        for lab in labels:
            if re.search(lab, line, re.I):
                m = pattern.search(line)
                if m:
                    return m.group(1)
    # unlabelled fallback (fewer candidates in a small doc, so keep it)
    m = pattern.search("\n".join(lines))
    return m.group(1) if m else None


def _plausible_name_words(cleaned: str) -> list[str] | None:
    """Return capitalized words if the string looks like a person's name."""
    words = cleaned.split()
    # A real name has >=2 letters per word and >=3 letters overall —
    # rejects bracket residue like the 's' left over from 'Given Name(s)'.
    if (1 <= len(words) <= 4
            and all(len(w) >= 2 for w in words)
            and sum(len(w) for w in words) >= 3
            and not _NAME_STOP.search(cleaned)):
        return [w.capitalize() for w in words]
    return None


def _extract_name(lines: list[str]) -> str | None:
    # Pass 1 — labelled lines, tolerant of OCR noise glued to the label
    # (real PaddleOCR output looks like '. a Elon Musk', 'Q AT aan').
    for line in lines:
        for lab in (r"surname", r"given name", r"\bname\b"):
            m = re.search(lab + r"\s*[:\-]?\s*(.{2,40})$", line, re.I)
            if m:
                cleaned = re.sub(r"[^A-Za-z\s]", " ", m.group(1)).strip()
                words = _plausible_name_words(cleaned)
                if words:
                    return " ".join(words)
    # Pass 2 — labelled value on the FOLLOWING line (passport layout:
    # 'Surname' / 'SHARMA' on separate lines). The candidate itself must not
    # be another field label ('Surname' → 'Given Name(s)' layout chains).
    for i, line in enumerate(lines):
        if re.search(r"surname|given name", line, re.I) and i + 1 < len(lines):
            candidate_line = lines[i + 1]
            if _FIELD_LINE.search(candidate_line):
                continue
            cleaned = re.sub(r"[^A-Za-z\s]", "", candidate_line).strip()
            words = _plausible_name_words(cleaned)
            if words:
                return " ".join(words)
    return None


# Lines carrying a known field label are never mined for name candidates.
_FIELD_LINE = re.compile(
    r"\b(passport|visa|country|code|type|no\.?|number|date|birth|expiry|issue|"
    r"sex|gender|nationality|address|blood|mrz|aadhaar|uidai|authority|"
    r"government|ministry|republic|department|income tax|election|"
    r"licen[cs]e|identification|name|given|surname)\b", re.I)


def _extract_name_fuzzy(lines: list[str]) -> str | None:
    """Last-resort name extraction when labels are unreadable (low confidence)."""
    best: str | None = None
    for line in lines:
        if _FIELD_LINE.search(line):
            continue
        for m in _TITLE_CASE_NAME.finditer(line):
            candidate = m.group(0)
            if _NAME_STOP.search(candidate):
                continue
            if best is None or len(candidate) > len(best):
                best = candidate
    return best.title() if best else None


# Document types that never carry an expiry field — requesting one would
# report a permanent false "missing".
_NO_EXPIRY_TYPES = {"aadhaar"}


def extract_document_fields(raw_text: str, fuzzy: bool = False) -> dict[str, Any]:
    """Extract the fields the SIH statement requires for each document type.

    With ``fuzzy=True`` the extractor falls back to label-free heuristics for
    fields it could not find; those are returned with ``?`` appended so
    validation can grade them as low-confidence instead of missing.
    """
    lines = _find_lines(raw_text)
    dtype = detect_document_type(raw_text)["document_type"]
    fields: dict[str, Any] = {}

    fuzzy_name = _extract_name_fuzzy(lines) if fuzzy else None
    fields["full_name"] = _extract_name(lines) or (fuzzy_name + "?" if fuzzy_name else None)
    fields["date_of_birth"] = _labelled_date(lines, [r"dob", r"date of birth", r"birth"])
    if fields["date_of_birth"] is None and fuzzy:
        for line in lines:
            m = _DATE_RE.search(line)
            if m and _plausible_birth(m.group(1)):
                fields["date_of_birth"] = m.group(1) + "?"
                break
    fields["gender"] = (_GENDER_RE.search(raw_text).group(2).capitalize()
                        if _GENDER_RE.search(raw_text) else None)

    if dtype == "passport":
        # prefer a properly-formatted number; if a label names the field but the
        # value is malformed, capture it anyway so validation can flag it
        fields["passport_number"] = _labelled_value(lines, [r"passport (?:no|number)", r"\bno\.?\s*$"], _PASSPORT_NO_RE) \
            or (_PASSPORT_NO_RE.search(raw_text).group(1) if _PASSPORT_NO_RE.search(raw_text) else None)
        if fields["passport_number"] is None:
            # label present but strict pattern failed (OCR noise / missing letter
            # prefix) — capture the labelled value so validation can grade it
            labelled = _labelled_value(lines, [r"passport (?:no|number)"], re.compile(r"\b([A-Z0-9]{6,12})\b"))
            if labelled:
                fields["passport_number"] = labelled
        fields["nationality"] = (_NATIONALITY_RE.search(raw_text).group(1).strip().title()
                                 if _NATIONALITY_RE.search(raw_text) else None)
        fields["date_of_expiry"] = _labelled_date(lines, [r"date of expiry", r"expiry", r"date of expire", r"valid until"])
        fields["date_of_issue"] = _labelled_date(lines, [r"date of issue", r"issue date"])
        fields["mrz_present"] = bool(_mrz_lines(raw_text))

    elif dtype == "visa":
        fields["visa_number"] = _labelled_value(lines, [r"visa (?:no|number)", r"visa ref"], _VISA_NO_RE)
        fields["visa_type"] = None
        for pat in (r"visa type[:\s]+([A-Za-z /-]{3,24}?)(?:\s{2,}|$|\n)", r"\b(entry|tourist|business|student|employment|transit|diplomatic)\s+visa\b"):
            m = re.search(pat, raw_text, re.I)
            if m:
                fields["visa_type"] = m.group(1).strip().title()
                break
        fields["entry"] = (m.group(1).title() if (m := re.search(r"\b(single|double|multiple)\b", raw_text, re.I)) else None)
        fields["stay_duration"] = (m.group(0) if (m := re.search(r"\b(\d{1,3}\s*(?:days|months|year[s]?))\b", raw_text, re.I)) else None)
        fields["date_of_expiry"] = _labelled_date(lines, [r"valid (?:until|till)", r"expiry", r"valid(?:ity)? (?:from|upto)"])
        fields["date_of_issue"] = _labelled_date(lines, [r"issue", r"issued on"])

    elif dtype == "driving_licence":
        fields["licence_number"] = _labelled_value(lines, [r"(?:dl|licen[cs]e)\s*(?:no|number)", r"\bno\b"], _DL_RE) \
            or (_DL_RE.search(raw_text).group(1) if _DL_RE.search(raw_text) else None)
        fields["date_of_expiry"] = _labelled_date(lines, [r"valid (?:till|until)", r"expiry", r"date of expiry"])
        fields["date_of_issue"] = _labelled_date(lines, [r"issue", r"issued"])
        fields["blood_group"] = (m.group(1) if (m := re.search(r"\b(blood\s*group|bg)\b[:\s]*([ABO][123+_-]?)", raw_text, re.I)) else None)

    elif dtype == "pan":
        fields["pan_number"] = (_PAN := re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")).search(raw_text).group(1) if _PAN.search(raw_text) else None
        fields["date_of_birth"] = fields.get("date_of_birth") or _labelled_date(lines, [r"dob", r"date of birth", r"birth"])

    elif dtype == "aadhaar":
        aad = re.search(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", raw_text)
        fields["aadhaar_number"] = aad.group(1) if aad else None
        fields["enrollment"] = None

    # Expiry also on generic documents (never on types that have no expiry)
    if "date_of_expiry" not in fields and dtype not in _NO_EXPIRY_TYPES:
        fields["date_of_expiry"] = _labelled_date(lines, [r"date of expiry", r"valid (?:until|till|upto)", r"expiry"])

    return fields


# ---------------------------------------------------------------------------
# Validation rules (Module 2)
# ---------------------------------------------------------------------------

def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            d = datetime.strptime(s, fmt).date()
            # 2-digit years: 25 → 2025, 98 → 1998 (pivot at 34, like passports)
            if d.year > date.today().year + 10:
                d = d.replace(year=d.year - 100)
            return d
        except ValueError:
            continue
    return None


def _plausible_birth(date_str: str) -> bool:
    d = _parse_date(date_str)
    if d is None:
        return False
    today = date.today()
    # A living person's birth date: 1900+ and at least 5 years ago.
    return 1900 <= d.year and d < today.replace(year=today.year - 5)


def _validate_date_string(s: str | None, field: str) -> dict[str, Any]:
    parsed = _parse_date(s)
    out: dict[str, Any] = {"field": field, "value": s, "status": "ok", "message": "valid date"}
    if s is None:
        out.update(status="missing", message="field not found in OCR text")
    elif parsed is None:
        out.update(status="invalid_format", message=f"'{s}' does not parse as DD/MM/YYYY")
    else:
        today = date.today()
        if parsed > today.replace(year=today.year + 20):
            out.update(status="implausible", message=f"date too far in the future: {parsed.isoformat()}")
        elif parsed.year < 1900:
            out.update(status="implausible", message=f"date too far in the past: {parsed.isoformat()}")
    return out


def _check_expiry(expiry: str | None) -> dict[str, Any]:
    d = _parse_date(expiry)
    if d is None:
        return {"field": "date_of_expiry", "value": expiry, "status": "missing" if not expiry else "invalid_format",
                "message": "expiry not readable" if not expiry else f"'{expiry}' not parseable"}
    today = date.today()
    days = (d - today).days
    if days < 0:
        return {"field": "date_of_expiry", "value": expiry, "status": "expired",
                "message": f"document expired {-days} days ago ({d.isoformat()})"}
    if days <= 30:
        return {"field": "date_of_expiry", "value": expiry, "status": "expiring_soon",
                "message": f"expires in {days} days ({d.isoformat()})"}
    return {"field": "date_of_expiry", "value": expiry, "status": "ok",
            "message": f"valid for {days} more days ({d.isoformat()})"}


# Official formats per type
_FORMAT_RULES: dict[str, tuple[str, re.Pattern]] = {
    "passport_number": ("passport number must be letter + 7 digits (e.g. Z1234567)", re.compile(r"^[A-Z][0-9]{7}$|^[A-Z]{2}[0-9]{6}$")),
    "pan_number": ("PAN must be 5 letters + 4 digits + 1 letter", re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")),
    "aadhaar_number": ("Aadhaar must be 12 digits (Verhoeff check not applied to OCR text)", re.compile(r"^\d{4}\s?\d{4}\s?\d{4}$")),
    "visa_number": ("visa number must be 8-12 digits", re.compile(r"^[0-9]{8,12}$")),
    "licence_number": ("DL format: state code + RTO + year + serial (e.g. KA0520190001234)", re.compile(r"^[A-Z]{2}[-\s]?\d{1,2}[-\s]?(?:19|20)\d{2}\d{6,8}$")),
}


def validate_document(raw_text: str) -> dict[str, Any]:
    """Module 2: run every rule, return per-field verdicts + a summary.

    Verdicts: ok / missing / invalid_format / implausible / expired / expiring_soon.
    The summary is informational — officers see exactly which rule fired.
    """
    fields = extract_document_fields(raw_text)
    dtype = detect_document_type(raw_text)["document_type"]
    # Noisy real-world OCR: retry with label-free fallbacks before declaring
    # a field missing. Fuzzy hits carry a trailing '?' and grade as low confidence.
    if any(fields.get(k) is None for k in ("full_name", "date_of_birth")):
        fields.update(extract_document_fields(raw_text, fuzzy=True))

    checks: list[dict[str, Any]] = []

    # dates
    dob = fields.get("date_of_birth")
    if isinstance(dob, str) and dob.endswith("?"):
        parsed = _parse_date(dob.rstrip("?"))
        checks.append({"field": "date_of_birth", "value": dob.rstrip("?"),
                       "status": "ok", "low_confidence": True,
                       "message": f"date {parsed.strftime('%d/%m/%Y')} found without a readable label" if parsed
                                  else f"'{dob.rstrip('?')}' does not parse as DD/MM/YYYY"})
        if parsed is None:
            checks[-1]["status"] = "invalid_format"
    else:
        checks.append(_validate_date_string(dob, "date_of_birth"))
    if dtype not in _NO_EXPIRY_TYPES:
        checks.append(_check_expiry(fields.get("date_of_expiry")))

    # name plausibility
    name = fields.get("full_name")
    if name is None:
        checks.append({"field": "full_name", "value": None, "status": "missing", "message": "name not found in OCR text"})
    elif isinstance(name, str) and name.endswith("?"):
        clean = name.rstrip("?")
        if _NAME_STOP.search(clean):
            checks.append({"field": "full_name", "value": clean, "status": "implausible", "message": "name candidate contains official boilerplate"})
        else:
            checks.append({"field": "full_name", "value": clean, "status": "ok", "low_confidence": True,
                           "message": f"name candidate '{clean}' found without a readable label — verify against the document"})
    elif _NAME_STOP.search(name):
        checks.append({"field": "full_name", "value": name, "status": "implausible", "message": "name contains official boilerplate"})
    else:
        checks.append({"field": "full_name", "value": name, "status": "ok", "message": "plausible name"})

    # format rules for the number fields present
    for fname, (desc, pat) in _FORMAT_RULES.items():
        val = fields.get(fname)
        if val is None:
            continue  # field absent: not a validation failure for this doc type
        ok = bool(pat.match(val.replace(" ", "").replace("-", "")) or pat.match(val))
        checks.append({"field": fname, "value": val, "status": "ok" if ok else "invalid_format",
                       "message": f"format ok ({desc})" if ok else f"format violation — expected {desc}"})

    # MRZ cross-check for passports: presence is expected on the biographical page
    if dtype == "passport":
        mrz_ok = bool(fields.get("mrz_present"))
        checks.append({"field": "mrz", "value": mrz_ok, "status": "ok" if mrz_ok else "missing",
                       "message": "MRZ detected" if mrz_ok else "MRZ not detected (photo crop or scan quality)"})

    n_issue = sum(1 for c in checks if c["status"] not in ("ok", "missing"))
    n_missing = sum(1 for c in checks if c["status"] == "missing")
    n_lowconf = sum(1 for c in checks if c.get("low_confidence"))
    verdict = "fail" if n_issue else ("incomplete" if n_missing else "pass")
    if n_lowconf and verdict == "pass":
        verdict = "low_confidence"
    return {
        "document_type": dtype,
        "fields": fields,
        "checks": checks,
        "summary": {
            "rules_applied": len(checks),
            "violations": n_issue,
            "missing_fields": n_missing,
            "low_confidence_fields": n_lowconf,
            "verdict": verdict,
            "note": "Validation verdicts are rule-based evidence for the reviewing officer — never an automatic decision.",
        },
    }
