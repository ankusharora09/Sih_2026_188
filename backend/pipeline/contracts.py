"""Data contracts for the screening pipeline stages.

Each stage returns a ``StageResultContract`` dataclass. The structure mirrors the
JSON contracts described in ``docs/PIPELINE_CONTRACTS.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class StageResultContract:
    stage: str
    status: str  # success | failed | unavailable | skipped
    confidence: Optional[float] = None
    result: Optional[Dict[str, Any]] = field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)
    errors: Optional[str] = None
    processing_time_ms: Optional[int] = None

# Helper enum‑like constants for statuses (optional but convenient)
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_UNAVAILABLE = "unavailable"
STATUS_SKIPPED = "skipped"
