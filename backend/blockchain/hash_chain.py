"""Hash-chain audit ledger implementation.

Each audit event is linked to the previous event via a SHA-256 hash over a
canonical JSON representation of the event data, the previous hash, and the
timestamp. This provides an immutable append-only log that can be verified
later.

Ordering note: Events are ordered by ``timestamp`` (not by UUID string, which
is not chronological). Within a single second, insertion order is preserved by
the timestamp itself (datetime precision is microseconds in Python).
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any

from ..db import models
from ..db.database import SessionLocal
from ..config import settings


def _canonical_json(data: Dict[str, Any]) -> str:
    """Return a deterministic JSON string with sorted keys.

    ``json.dumps`` with ``sort_keys=True`` and no whitespace ensures the same
    representation across runs.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _compute_hash(previous_hash: str, event: Dict[str, Any]) -> str:
    """Compute SHA-256 hash for an event.

    The hash input is the concatenation of ``previous_hash`` + ``timestamp``
    (ISO format) + a canonical JSON representation of the *event* fields
    (excluding the timestamp itself to stay JSON-serializable).

    This function is deterministic: given the same inputs it always returns the
    same hash.
    """
    # timestamp may be a datetime object or a string from DB
    ts_val = event["timestamp"]
    if isinstance(ts_val, datetime):
        timestamp = ts_val.isoformat()
    else:
        timestamp = str(ts_val)

    # Build a serializable copy of the event without the datetime object
    event_copy = {k: v for k, v in event.items() if k != "timestamp"}
    payload = {
        "previous_hash": previous_hash,
        "timestamp": timestamp,
        "event": event_copy,
    }
    return hashlib.sha256(_canonical_json(payload).encode()).hexdigest()


class HashChain:
    """Simple wrapper around the ``AuditEvent`` table.

    Usage example::

        chain = HashChain(db_session)
        chain.append(
            actor_id="user-1",
            event_type="screening_started",
            case_id="c1",
            screening_run_id="r1",
            meta={},
        )

    The chain tip (``previous_hash``) is determined by reading the event with
    the latest ``timestamp`` at construction time. Callers that append multiple
    events sequentially via the same instance will always see the correct tip
    because ``self.previous_hash`` is updated after each ``append()``.
    """

    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()
        # Retrieve the latest hash (or empty string for genesis).
        # Order by timestamp DESC to ensure chronological ordering, not UUID ordering.
        last = (
            self.db.query(models.AuditEvent)
            .order_by(models.AuditEvent.timestamp.desc())
            .first()
        )
        self.previous_hash = last.current_hash if last else ""

    def append(
        self,
        actor_id: str,
        event_type: str,
        case_id: Optional[str] = None,
        screening_run_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> models.AuditEvent:
        """Create a new audit event and store it.

        Returns the persisted ``AuditEvent`` instance.
        """
        meta = meta or {}
        timestamp = datetime.utcnow()
        event_payload = {
            "actor_id": actor_id,
            "event_type": event_type,
            "case_id": case_id,
            "screening_run_id": screening_run_id,
            "meta": meta,
            "timestamp": timestamp,
        }
        # Compute hash based on previous hash and this event's payload
        current_hash = _compute_hash(self.previous_hash, event_payload)
        audit = models.AuditEvent(
            timestamp=timestamp,
            actor_id=actor_id,
            event_type=event_type,
            case_id=case_id,
            screening_run_id=screening_run_id,
            previous_hash=self.previous_hash,
            current_hash=current_hash,
            meta=meta,
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        # Update the chain tip for the next append() on this instance
        self.previous_hash = current_hash
        return audit

    def verify_chain(self) -> bool:
        """Verify the integrity of every event in the audit chain.

        Strategy: for each event, recompute its ``current_hash`` from its
        stored ``previous_hash`` and its event fields. If the stored
        ``current_hash`` matches the recomputed value, the event itself has not
        been tampered with.

        Additionally verify that each event's ``previous_hash`` equals the
        ``current_hash`` of the chronologically preceding event (ordered by
        ``timestamp``).

        Returns ``True`` if every event passes both checks; ``False`` otherwise.

        .. note::
            Events are ordered by ``timestamp`` to reflect insertion order.
            UUID-based ordering would be incorrect because UUIDs are not
            monotonic.
        """
        events = (
            self.db.query(models.AuditEvent)
            .order_by(models.AuditEvent.timestamp.asc())
            .all()
        )
        if not events:
            return True  # Empty chain is vacuously valid

        prev_hash = ""
        for ev in events:
            # 1. Recompute the hash from stored previous_hash and event fields
            event_payload = {
                "event_type": ev.event_type,
                "timestamp": ev.timestamp,
                "meta": ev.meta,
                "case_id": ev.case_id,
                "screening_run_id": ev.screening_run_id,
                "actor_id": ev.actor_id,
            }
            expected_hash = _compute_hash(ev.previous_hash, event_payload)
            if ev.current_hash != expected_hash:
                return False  # Hash mismatch – event may have been tampered with

            # 2. Verify the chain linkage: stored previous_hash must equal
            #    the preceding event's current_hash (or "" for genesis).
            if ev.previous_hash != prev_hash:
                return False  # Chain is broken – events are not linked

            prev_hash = ev.current_hash

        return True


# Convenience function for services to record an audit entry
def record_audit(
    db_session,
    actor_id: str,
    event_type: str,
    case_id: Optional[str] = None,
    screening_run_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> models.AuditEvent:
    """Append a single audit event to the hash-chain ledger.

    This creates a new ``HashChain`` instance (which reads the current chain
    tip from the DB), appends the event, and commits.
    """
    chain = HashChain(db_session)
    return chain.append(
        actor_id=actor_id,
        event_type=event_type,
        case_id=case_id,
        screening_run_id=screening_run_id,
        meta=meta,
    )
