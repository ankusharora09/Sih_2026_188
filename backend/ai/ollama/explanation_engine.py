"""Ollama explanation layer – generates natural‑language explanations for a screening run.
"""

from __future__ import annotations

import json
import time
try:
    import requests
except ImportError:
    requests = None
from typing import Dict, Any

from ...config import settings

_STAGE_LABELS = {
    "tampering": "Document Tampering",
    "liveness": "Liveness Check",
    "deepfake": "Deepfake / Synthetic Media",
    "face_mismatch": "Face Verification",
    "ocr_confidence": "OCR Extraction",
    "anomaly": "Cross-Case Anomaly",
}


class ExplanationEngine:
    """Generates an explanation using Ollama if available, otherwise a deterministic template.
    """

    def __init__(self):
        self.url = getattr(settings, "OLLAMA_URL", "")
        self.model = getattr(settings, "OLLAMA_MODEL", "")
        self.timeout = getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 5)

    def _ollama_call(self, payload: Dict[str, Any]) -> str:
        if not self.url or not self.model or not requests:
            raise RuntimeError("Ollama configuration missing or requests library unavailable")
        request_body = {
            "model": self.model,
            "prompt": payload["prompt"],
        }
        resp = requests.post(self.url, json=request_body, timeout=self.timeout)
        resp.raise_for_status()
        # Ollama returns a JSON with "response" field containing the text.
        data = resp.json()
        return data.get("response", "")

    def generate(self, risk_result: Dict[str, Any]) -> str:
        """Generate explanation.

        If Ollama is reachable, use it; otherwise return a deterministic template.
        """
        prompt = self._build_prompt(risk_result)
        try:
            return self._ollama_call({"prompt": prompt})
        except Exception:
            # Fallback – deterministic template.
            return self._fallback_explanation(risk_result)

    def _build_prompt(self, risk_result: Dict[str, Any]) -> str:
        """Summarise the risk engine's own contribution details for the LLM."""
        lines = ["Explain the screening findings concisely:"]
        lines.append(f"Risk score: {risk_result.get('risk_score')} (level: {risk_result.get('risk_level')})")
        for detail in risk_result.get("contribution_details") or []:
            lines.append(f"- {detail.get('signal')}: {detail.get('reason')} "
                         f"(value: {detail.get('value')}, threshold: {detail.get('threshold')})")
        return "\n".join(lines)

    def _fallback_explanation(self, risk_result: Dict[str, Any]) -> str:
        """Deterministic explanation derived from the risk engine's structured output."""
        lines = ["=== AI Screening Summary ==="]
        lines.append(f"Risk Score: {risk_result.get('risk_score', 0)}/100  |  Level: {risk_result.get('risk_level', 'UNKNOWN')}")

        triggered = risk_result.get("triggered_rules") or []
        lines.append(f"Triggered alerts: {', '.join(triggered)}" if triggered else "No risk rules triggered.")

        factors = risk_result.get("risk_factors") or []
        if factors:
            lines.append("")
            lines.append("Risk factors:")
            for f in factors:
                lines.append(f"  - {f.get('text', 'No signal.')}")

        gaps = risk_result.get("verification_gaps") or []
        if gaps:
            lines.append("")
            lines.append("Verification gaps (not counted as evidence of fraud):")
            for g in gaps:
                lines.append(f"  - {g.get('text', 'Verification not completed.')}")

        verification = risk_result.get("verification")
        if verification:
            lines.append("")
            lines.append(f"Verification: {verification.get('executed_count', 0)}/{verification.get('total', 0)} decisive checks executed.")

        return "\n".join(lines)
