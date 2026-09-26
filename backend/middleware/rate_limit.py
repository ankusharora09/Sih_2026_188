"""Rate limiting middleware using Redis (if configured).

Applies a simple token bucket per user (identified by JWT subject) per minute.
If Redis is unavailable, the middleware becomes a no‑op.
"""

from __future__ import annotations

import time
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..utils.redis_client import redis_client

# Default limit, can be overridden via environment variable RATE_LIMIT
from ..config import settings
DEFAULT_RATE_LIMIT = getattr(settings, "RATE_LIMIT", 60)  # 60 requests per minute per user


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = DEFAULT_RATE_LIMIT):
        super().__init__(app)
        self.limit = limit

    async def dispatch(self, request: Request, call_next):
        # If Redis not configured, skip limiting
        try:
            redis_client._ensure()
        except Exception:
            return await call_next(request)

        # Identify user – use auth token if available; fallback to IP
        user_id = request.client.host
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            # Simple decode without verification (lightweight) – reuse auth decode
            from ..security.auth import decode_access_token
            try:
                payload = decode_access_token(token[7:])
                user_id = payload.get("sub", user_id)
            except Exception:
                pass

        # Key format: rate:<user_id>:<epoch_minute>
        epoch_minute = int(time.time() // 60)
        key = f"rate:{user_id}:{epoch_minute}"
        try:
            count = redis_client.incr(key)
            # Ensure key expires after a minute
            redis_client._client.expire(key, 61)
        except Exception:
            # If Redis fails, skip limiting
            return await call_next(request)

        if count > self.limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        return await call_next(request)
