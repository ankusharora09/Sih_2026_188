# Audit / Blockchain Design

The audit subsystem provides a **tamper‑evident, append‑only log** of every important event in the identity‑screening workflow. In Phase 1 the chain resides in the relational database; Phase 5 will optionally anchor hashes to a permissioned Hyperledger Fabric ledger.

---

## 1. Event Structure

Each audit event is a JSON record stored in the `audit_events` table (or collection). The required fields are:

```json
{
  "event_id": "uuid",
  "timestamp": "iso8601",
  "actor": "user-id",
  "event_type": "stage_completed|risk_scored|case_created|...",
  "case_id": "uuid",
  "screening_run_id": "uuid",
  "previous_hash": "sha256:...",
  "current_hash": "sha256:...",
  "metadata": { "stage": "ocr", "status": "completed" }
}
```

- `previous_hash` is the `current_hash` of the preceding event for the **same case** (or the genesis hash if this is the first event).
- `current_hash` is computed deterministically as:
  ```
  hash(previous_hash + deterministic_serialization(event_payload))
  ```
- `event_payload` includes **only** non‑PII fields; any PII is stored encrypted elsewhere and referenced by hash.

---

## 2. Hash‑Chain Creation

1. When a new case is created, a **GENESIS** event is inserted with a fixed `previous_hash` of `"0"`.
2. For each subsequent stage (OCR, tampering, etc.) the orchestrator builds the event JSON, serializes it in a canonical order (sorted keys), and computes the SHA‑256 hash.
3. The `current_hash` becomes the `previous_hash` for the next event.

The chain guarantees **integrity**: any modification of an earlier event changes its hash, breaking the chain verification.

---

## 3. Integrity Verification

A verification routine recomputes the hash chain for a given `case_id`:

```python
prev = "0"
for event in ordered_events:
    payload = canonical_json(event_without_hashes)
    expected = sha256(prev + payload)
    if expected != event["current_hash"]:
        raise IntegrityError(event["event_id"])
    prev = event["current_hash"]
```

If all hashes match, the audit trail is intact.

---

## 4. Future Hyperledger Fabric Integration

- **Anchor Transaction**: Periodically (e.g., after each screening run) the `current_hash` is written to a Fabric transaction, providing an immutable external checkpoint.
- **Gateway Adapter**: A lightweight service signs the hash with the node’s private key and submits it via Fabric SDK.
- **On‑Chain Record**: Stores `{ case_id, run_id, hash, timestamp }`. The on‑chain hash can be used to verify the off‑chain chain with a simple Merkle proof.

The design ensures **no raw PII** or large binary data is ever placed on the blockchain—only cryptographic hashes and minimal metadata.

---

## 5. Audit Query API (see `docs/API_CONTRACTS.md`)

- **GET** `/cases/{case_id}/audit` – returns the ordered list of audit events for the case.
- Clients can request verification status; the server can return a boolean `integrity_ok` alongside the event list.

---

## 6. Storage Considerations

- Index on `case_id` and `timestamp` for efficient retrieval.
- Retention policy: audit events are immutable; they may be archived after a configurable period (e.g., 5 years) but the hash chain must remain verifiable.

---

*The audit design satisfies the critical architecture rule: **Never store raw PII, document images, or face images on the blockchain**. Only deterministic hashes and minimal metadata are recorded, preserving privacy while providing proof of integrity.*
