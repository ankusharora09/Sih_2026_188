"""Hyperledger Fabric stub – minimal interface for audit ledger integration.

In production the audit events would be written to a Fabric channel. For the
demo we provide a no‑op implementation that satisfies the same API used by the
HashChain class. This keeps the codebase importable without requiring the
heavy Fabric SDK or a running network.
"""

from __future__ import annotations

from typing import Any, Dict


class HyperledgerClient:
    """Very small subset of a Fabric client.

    The real client would submit a transaction to a chaincode function. Here we
    simply expose ``submit_event`` which returns a dict mimicking a transaction
    receipt. All calls succeed and no external services are contacted.
    """

    def __init__(self, connection_profile: str | None = None):
        # ``connection_profile`` would point to a YAML/JSON file in a real
        # deployment. It is unused in the stub.
        self.connection_profile = connection_profile

    def submit_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Pretend to submit ``event`` to the ledger and return a receipt.

        The receipt contains an ``event_id`` (a UUID string) and a ``status``
        field. In a production implementation the ID would be the transaction ID
        and ``status`` would reflect commit success.
        """
        from uuid import uuid4

        return {"event_id": str(uuid4()), "status": "committed", "event": event}

    # The stub could expose additional lifecycle methods (connect, close) if the
    # calling code ever needs them, but the current codebase only requires the
    # ``submit_event`` method.

# Export a singleton for convenience – the same instance is reused across the
# application, mirroring the lightweight pattern used for the Redis client.
hyperledger_client = HyperledgerClient()
