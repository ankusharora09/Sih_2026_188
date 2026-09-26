"""Deterministic risk engine – combines stage outcomes into a numeric risk score.
"""

from __future__ import annotations

import math
from typing import Dict, Any, List

from ..config import settings


_NON_DECISIVE = {"unavailable", "skipped", "failed"}

# Signals that must EXECUTE for an identity to be considered verified.
# `anomaly` is cross-case intelligence, not a per-case verification step.
DECISIVE_SIGNALS = ("tampering", "face_mismatch", "liveness", "deepfake",
                    "ocr_confidence", "document_validation")

# Mandatory document fields: missing any of these forces human review.
_MANDATORY_FIELDS = {"full_name", "date_of_birth", "date_of_expiry"}


class RiskEngine:
    """Computes a deterministic risk score based on configurable weights.

    Skipped / unavailable / failed stages are not treated as incriminating.
    They set review_required instead of adding full weight.
    """

    def __init__(self):
        self.weights = getattr(settings, "RISK_WEIGHTS", {
            "tampering": 0.25,
            "liveness": 0.15,
            "deepfake": 0.20,
            "face_mismatch": 0.15,
            "ocr_confidence": 0.10,
            "anomaly": 0.10,
            "document_validation": 0.05,
        })
        self.low_th = getattr(settings, "RISK_LEVEL_LOW", 20)
        self.med_th = getattr(settings, "RISK_LEVEL_MEDIUM", 50)
        self.high_th = getattr(settings, "RISK_LEVEL_HIGH", 80)

    def _normalize_confidence(self, conf: Any) -> float | None:
        if conf is None:
            return None
        try:
            value = float(conf)
        except (TypeError, ValueError):
            return None
        if value > 1.0:
            value = value / 100.0
        return max(0.0, min(value, 1.0))

    def _stage_risk(self, key: str, result: Dict[str, Any], status: str | None = None) -> Dict[str, Any]:
        weight = float(self.weights.get(key, 0))
        status = status or (result or {}).get("status") or "unknown"
        if status in _NON_DECISIVE:
            stage_reason = (result or {}).get("reason") or (result or {}).get("note") or (result or {}).get("error")
            default = {
                "skipped": "Not run — required input was not provided.",
                "unavailable": "Service or model unavailable.",
                "failed": "Stage execution failed.",
            }[status]
            officer_reason = f"{str(stage_reason).strip().capitalize().rstrip('.')}." if stage_reason else default
            return {
                "signal": key,
                "source": key,
                "value": None,
                "threshold": None,
                "weight": weight,
                "contribution": 0.0,
                "reason": f"stage_{status}_not_used_as_guilt",
                "officer_reason": officer_reason,
                "review": True,
                "status": status,
            }

        contribution = 0.0
        review = False
        reason = "no_signal"
        officer_reason = "No signal."
        value = None
        threshold = None

        if key == "tampering":
            value = result.get("tampered")
            threshold = result.get("score_threshold") or getattr(settings, "TAMPERING_SCORE_THRESHOLD", 0.5)
            if result.get("tampered"):
                contribution = weight
                reason = "tampering_detected"
                officer_reason = "Tampering signals detected in the document."
            else:
                reason = "no_tampering_signal"
                officer_reason = "No tampering signal detected."
        elif key == "liveness":
            value = result.get("is_live")
            threshold = True
            if value is False:
                contribution = weight
                reason = "liveness_failed"
                officer_reason = "Subject failed the liveness check."
            else:
                reason = "live_capture_accepted"
                officer_reason = "Live capture verified."
        elif key == "deepfake":
            try:
                score = float(result.get("score") or 0)
            except (TypeError, ValueError):
                score = 0.0
            value = score
            threshold = result.get("threshold")
            contribution = weight * max(0.0, min(score, 1.0))
            if contribution:
                reason = "deepfake_score_weighted"
                officer_reason = "Synthetic-media indicators present."
            else:
                reason = "deepfake_score_negligible"
                officer_reason = "No synthetic-media signal detected."
        elif key == "face_mismatch":
            value = result.get("match")
            threshold = result.get("threshold")
            if value is False:
                contribution = weight
                reason = "face_mismatch"
                officer_reason = "Face mismatch between document and capture."
            elif value is True:
                reason = "face_match"
                officer_reason = "Face match confirmed."
            # Ambiguous biometric evidence (no face, multiple faces) must not
            # pass silently: flag for human review without adding risk weight.
            if result.get("uncertainty") in ("multiple_faces", "no_face", "uncalibrated_fallback"):
                review = True
                if reason == "no_signal":
                    reason = f"face_analysis_{result.get('uncertainty')}"
                    officer_reason = f"Biometric evidence inconclusive ({str(result.get('uncertainty')).replace('_', ' ')}) — manual review required."
            elif value is None:
                review = True
                reason = "face_match_unknown"
                officer_reason = "Face comparison inconclusive — manual review required."
        elif key == "ocr_confidence":
            conf = self._normalize_confidence(result.get("confidence"))
            value = conf
            threshold = 0.4
            if conf is None:
                review = True
                reason = "ocr_confidence_missing"
                officer_reason = "OCR confidence unavailable."
            else:
                contribution = weight * (1 - conf)
                if conf < threshold:
                    reason = "low_ocr_confidence"
                    officer_reason = f"Low OCR confidence ({conf:.0%})."
                else:
                    reason = "ocr_confidence_acceptable"
                    officer_reason = f"OCR confidence acceptable ({conf:.0%})."
        elif key == "anomaly":
            try:
                score = float(result.get("score") or 0)
            except (TypeError, ValueError):
                score = 0.0
            value = score
            threshold = 0.25
            anomalies = result.get("anomalies") or []
            if anomalies:
                contribution = weight * max(0.0, min(score, 1.0))
                reason = "cross_case_anomaly"
                officer_reason = f"Linked records found in {len(anomalies)} other case(s)."
            else:
                reason = "no_anomaly_signal"
                officer_reason = "No cross-case links found."
        elif key == "document_validation":
            # Rule-based validation verdicts (expired dates, format violations,
            # implausible values). Fractional contribution per hard violation.
            summary = ((result or {}).get("validation") or {}).get("summary") or {}
            violations = int(summary.get("violations") or 0)
            value = violations
            threshold = 0
            if violations:
                contribution = weight * min(1.0, 0.5 + 0.25 * (violations - 1))
                reason = f"validation_violations_{violations}"
                officer_reason = f"{violations} document validation rule violation(s)."
                if any(c.get("status") == "expired" for c in (result.get("validation") or {}).get("checks", [])):
                    reason = "document_expired"
                    officer_reason = "Document is expired."
            else:
                verdict = summary.get("verdict") or "unknown"
                reason = f"validation_{verdict}"
                officer_reason = {
                    "pass": "All document validation rules passed.",
                    "incomplete": "Validation incomplete — mandatory fields missing.",
                }.get(verdict, f"Document validation verdict: {verdict}.")

        return {
            "signal": key,
            "source": key,
            "value": value,
            "threshold": threshold,
            "weight": weight,
            "contribution": contribution,
            "reason": reason,
            "officer_reason": officer_reason,
            "review": review,
            "status": status,
        }

    @staticmethod
    def _mandatory_fields_missing(validation_result: Dict[str, Any]) -> List[str]:
        checks = ((validation_result or {}).get("validation") or {}).get("checks") or []
        return sorted({c.get("field") for c in checks
                       if c.get("status") == "missing" and c.get("field") in _MANDATORY_FIELDS})

    def compute(self, stage_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        total_weight = sum(self.weights.values()) or 1.0
        risk_sum = 0.0
        contributions: Dict[str, float] = {}
        details: List[Dict[str, Any]] = []
        triggered_rules: List[str] = []
        review_required = False
        executed: List[str] = []
        executed_weight = 0.0
        missing_fields: List[str] = []

        for key, res in stage_results.items():
            status = (res or {}).get("status") or "unknown"
            row = self._stage_risk(key, res or {})
            details.append(row)
            contributions[key] = row["contribution"]
            if row["contribution"] > 0:
                triggered_rules.append(key)
            if row.get("review"):
                review_required = True
            risk_sum += row["contribution"]
            if key in DECISIVE_SIGNALS:
                if status == "success":
                    executed.append(key)
                    executed_weight += float(self.weights.get(key, 0))
                if key == "document_validation":
                    missing_fields = self._mandatory_fields_missing(res)

        risk_score = int(math.floor((risk_sum / total_weight) * 100))
        if risk_score < self.low_th:
            level = "low"
        elif risk_score < self.high_th:
            level = "medium"
        else:
            level = "high"

        # Verification completeness: how many decisive checks actually ran.
        pending = [k for k in DECISIVE_SIGNALS if k not in executed]
        verification = {
            "executed": executed,
            "pending": pending,
            "executed_count": len(executed),
            "total": len(DECISIVE_SIGNALS),
            "percent": int(round(100 * len(executed) / len(DECISIVE_SIGNALS))),
        }
        # Confidence that the risk score itself is based on enough evidence:
        # executed decisive weight over total decisive weight.
        decisive_weight_total = sum(float(self.weights.get(k, 0)) for k in DECISIVE_SIGNALS) or 1.0
        confidence_score = int(round(100 * executed_weight / decisive_weight_total))

        # Deterministic decision: evidence gaps outrank a quiet score —
        # "no evidence of fraud" is NOT "identity fully verified".
        if review_required or missing_fields:
            decision = "REVIEW_REQUIRED"
        elif risk_score >= self.high_th:
            decision = "REJECT"
        elif risk_score >= self.med_th:
            decision = "REVIEW"
        else:
            decision = "VERIFY"

        # Incomplete evidence must not look "safe"; it also must not look HIGH.
        display_level = "REVIEW_REQUIRED" if (decision == "REVIEW_REQUIRED" and level == "low") else level

        # Officer-facing summaries (never expose internal reason codes).
        risk_factors = [
            {"signal": d["signal"], "contribution": d["contribution"], "text": d["officer_reason"]}
            for d in details if d["status"] not in _NON_DECISIVE
        ]
        verification_gaps = [
            {"signal": d["signal"], "status": d["status"], "text": d["officer_reason"]}
            for d in details if d["status"] in _NON_DECISIVE
        ]

        return {
            "risk_score": risk_score,
            "risk_level": display_level,
            "numeric_level": level,
            "review_required": review_required,
            "triggered_rules": triggered_rules,
            "contributions": contributions,
            "contribution_details": details,
            "verification": verification,
            "verification_completeness": verification["percent"],
            "confidence_score": confidence_score,
            "decision_status": decision,
            "missing_mandatory_fields": missing_fields,
            "risk_factors": risk_factors,
            "verification_gaps": verification_gaps,
        }
