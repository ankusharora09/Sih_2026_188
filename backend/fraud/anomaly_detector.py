"""Anomaly detection package – identifies suspicious patterns across cases.
"""

from __future__ import annotations

from typing import List, Dict, Any

from ..db import models
from ..config import settings


class AnomalyDetector:
    """Detects simple cross‑case anomalies.

    Current implementation checks for:
    * Duplicate document content hashes across cases.
    * Reused subject names across cases.
    * Reused face similarity (if stored) – not implemented for demo.
    """

    def __init__(self, db_session):
        self.db = db_session

    def detect_for_case(self, case_id: str) -> dict:
        """Run anomaly detection for a single case and return structured result.

        Returns a dict with keys:
        - ``status``: ``"success"`` or ``"failed"``
        - ``anomalies``: list of description strings
        - ``score``: 0‑1 confidence (higher = more anomalous)
        """
        try:
            anomalies: List[str] = []
            # Duplicate content hash detection
            subquery = (
                self.db.query(models.DocumentFile.content_hash)
                .filter(models.DocumentFile.case_id == case_id)
                .scalar_subquery()
            )
            duplicate_hashes = (
                self.db.query(models.DocumentFile.content_hash)
                .filter(models.DocumentFile.content_hash.in_(subquery))
                .filter(models.DocumentFile.case_id != case_id)
                .distinct()
                .all()
            )
            if duplicate_hashes:
                anomalies.append(f"Duplicate document hash found in other cases ({len(duplicate_hashes)} hashes)")


            # Duplicate subject name detection
            case = self.db.query(models.Case).filter(models.Case.id == case_id).first()
            if case and case.subject_name:
                other_cases = (
                    self.db.query(models.Case)
                    .filter(models.Case.subject_name == case.subject_name, models.Case.id != case_id)
                    .count()
                )
                if other_cases:
                    anomalies.append(f"Subject name '{case.subject_name}' appears in {other_cases} other case(s)")

            # Reused ID number with a different subject name (Phase 8):
            # strongest identity-reuse signal short of face-embedding reuse.
            own_id = self._extracted_id_number(case_id)
            if own_id:
                ocr_rows = (
                    self.db.query(models.StageResult)
                    .join(models.ScreeningRun, models.ScreeningRun.id == models.StageResult.run_id)
                    .filter(models.StageResult.stage == "ocr",
                            models.ScreeningRun.case_id != case_id)
                    .all()
                )
                reuse_count = 0
                different_name_seen = False
                for row in ocr_rows:
                    fields = ((row.result or {}).get("fields") or {})
                    if fields.get("extracted_id_number") != own_id:
                        continue
                    reuse_count += 1
                    run = self.db.query(models.ScreeningRun).filter(
                        models.ScreeningRun.id == row.run_id).first()
                    other_case = (
                        self.db.query(models.Case).filter(models.Case.id == run.case_id).first()
                        if run else None
                    )
                    if (other_case and case and case.subject_name
                            and other_case.subject_name
                            and other_case.subject_name != case.subject_name):
                        different_name_seen = True
                if reuse_count:
                    if different_name_seen:
                        anomalies.append(
                            f"ID number ending '...{own_id[-4:]}' appears in another case "
                            f"with a different subject name (repeated identity signal)"
                        )
                    else:
                        anomalies.append(
                            f"ID number ending '...{own_id[-4:]}' appears in {reuse_count} other case(s)"
                        )

            score = min(len(anomalies) * 0.25, 1.0)  # simple scaling
            return {
                "status": "success",
                "anomalies": anomalies,
                "score": score,
            }
        except Exception as exc:  # pragma: no cover – defensive
            return {"status": "failed", "error": str(exc)}

    def _extracted_id_number(self, case_id: str) -> str | None:
        """Latest OCR-extracted ID number for this case, if any."""
        row = (
            self.db.query(models.StageResult)
            .join(models.ScreeningRun, models.ScreeningRun.id == models.StageResult.run_id)
            .filter(models.StageResult.stage == "ocr",
                    models.ScreeningRun.case_id == case_id)
            .order_by(models.ScreeningRun.started_at.desc())
            .first()
        )
        if not row:
            return None
        return ((row.result or {}).get("fields") or {}).get("extracted_id_number")
