"""Authentication utilities for development.

Provides a ``dev_token`` endpoint that issues a JWT signed with the ``SECRET_KEY``.
The token payload contains ``user_id`` and ``role``. ``get_current_user`` is a
FastAPI dependency that validates the token and returns a simple user model.
"""

from __future__ import annotations

import base64
import json
import hmac
import hashlib

from typing import List, Optional
import time
from fastapi import Depends, HTTPException, status

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def _b64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)

def jwt_encode(payload: dict, secret: str, algorithm: str = "HS256") -> str:
    if algorithm != "HS256":
        raise ValueError("Only HS256 is supported in this minimal impl")
    header = {"alg": algorithm, "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(',', ':')).encode())
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(',', ':')).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def jwt_decode(token: str, secret: str, algorithms: List[str]) -> dict:
    # Very small subset: verify signature and return payload.
    if "HS256" not in algorithms:
        raise ValueError("Only HS256 is supported in this minimal impl")
    try:
        header_b64, payload_b64, signature_b64 = token.split('.')
    except ValueError:
        raise ValueError("Invalid token format")
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url_encode(expected_sig), signature_b64):
        raise ValueError("Signature verification failed")
    payload_bytes = _b64url_decode(payload_b64)
    return json.loads(payload_bytes)

from ..config import settings

ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 3600  # 1 hour for dev tokens


class AuthError(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def create_access_token(*, user_id: str, role: str, expires_delta: Optional[int] = None) -> str:
    to_encode = {"sub": user_id, "role": role, "iat": int(time.time())}
    if expires_delta is None:
        expires_delta = TOKEN_EXPIRE_SECONDS
    to_encode.update({"exp": int(time.time()) + expires_delta})
    encoded_jwt = jwt_encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt_decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception as e:
        raise AuthError(str(e))


# Simple user model returned by the dependency – not a full ORM object.
class SimpleUser:
    def __init__(self, user_id: str, role: str):
        self.id = user_id
        self.role = role


from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Use simple HTTP Bearer scheme for Swagger UI – token can be entered directly.
oauth_scheme = HTTPBearer()

def get_current_user(token: HTTPAuthorizationCredentials = Depends(oauth_scheme)) -> SimpleUser:
    if not token:
        raise AuthError("Missing token")
    payload = decode_access_token(token.credentials)
    user_id: str = payload.get("sub")
    role: str = payload.get("role")
    if user_id is None or role is None:
        raise AuthError("Invalid token payload")
    return SimpleUser(user_id=user_id, role=role)
