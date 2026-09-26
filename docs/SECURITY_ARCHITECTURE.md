# Security Architecture

## 1. Authentication

- **Development** – JWT access‑token scaffold (`/api/v1/auth/dev-token`). Short‑lived tokens signed with a secret stored in environment (`SECRET_KEY`).
- **Production** – Replace with OAuth2/OIDC provider (e.g., Keycloak, Auth0). Tokens issued by the provider are validated by the API gateway.
- Tokens contain `sub` (user ID) and `roles` claim for RBAC.

## 2. RBAC (Role‑Based Access Control)

| Role | Permissions |
|---|---|
| **OFFICER** | Create/review cases, upload files, trigger screening, view audit events for own cases.
| **ADMIN** | Manage users/roles, configure system settings, view all audit events, delete/expire cases.
| **AUDITOR** | Read‑only access to audit logs and case evidence across all cases.

RBAC enforcement is applied at the FastAPI dependency level; each endpoint checks the caller's role before proceeding.

## 3. Transport Security

- TLS termination at the API gateway (HTTPS enforced in production). Development can use HTTP for local testing.
- Enforce `Strict-Transport-Security` header in production.

## 4. Rate Limiting & Abuse Protection

- Global per‑IP request rate limit (e.g., 100 req/min).
- Per‑user upload size limits (e.g., max 10 MB per file, total 50 MB per case).
- MIME type validation for uploaded files.
- Hook to an antivirus / malware scanner for every upload (e.g., ClamAV integration).

## 5. Input Validation

- All JSON payloads validated against Pydantic schemas.
- File uploads scanned for malicious content; reject suspicious files.
- Strict schema for `case_id`, `file_id`, and other identifiers (UUID format).

## 6. Encryption at Rest

- Database‑level encryption for sensitive columns (PII) using field‑level encryption (e.g., `cryptography.Fernet`). Encryption keys loaded from environment (`ENCRYPTION_KEY`).
- Object storage (e.g., S3‑compatible) encrypts files server‑side (SSE‑S3) and uses signed URLs for temporary access.

## 7. Secret Management

- No secrets hard‑coded in source.
- All secrets (DB passwords, JWT secret, encryption keys) read from environment variables or a secret manager (e.g., Docker secrets, Azure Key Vault) in production.

## 8. Audit Logging

- Every privileged action (case creation, file upload, screening trigger, risk‑score generation, audit chain update) emits an audit event (see `docs/AUDIT_BLOCKCHAIN.md`).
- Logs are structured JSON, written to a rotating file (`logs/audit.log`) and optionally streamed to a centralized logging service.
- Sensitive data (raw biometric images, full document text) never appears in logs; only hashes and metadata are logged.

## 9. Threat Model Overview

| Threat | Mitigation |
|---|---|
| Unauthorized data access | JWT/OIDC authentication, RBAC, TLS, encrypted storage. |
| Replay attacks | Short‑lived JWTs, nonce / correlation IDs on each request. |
| Data exfiltration | Strict file‑type validation, size limits, no raw PII stored on chain. |
| Tampering of audit records | Append‑only hash chain, future Hyperledger Fabric anchoring. |
| Model / AI manipulation | Mock adapters clearly labeled; production models locked behind internal services with access controls. |

## 10. Future Hardening (Phase 5)

- Mutual TLS between micro‑services.
- Hardware security module (HSM) for key management.
- Fine‑grained ABAC policies for data‑subject access.
- Automated vulnerability scanning and dependency checking.
- Continuous compliance auditing (e.g., ISO 27001).

---

*All security controls are designed to be configurable via environment variables, enabling a secure default configuration for production while keeping development simple.*
