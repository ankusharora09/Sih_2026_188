"""Simple Redis client wrapper.

Provides get, set, incr, delete operations with JSON serialization.
If REDIS_URL is not set, the client is disabled and raises RuntimeError on use.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from ..config import settings


class RedisClient:
    def __init__(self) -> None:
        self._url = settings.REDIS_URL
        self._client = None
        if self._url:
            try:
                import redis
                self._client = redis.from_url(self._url)
            except Exception as e:
                # Fail fast – raise when accessed
                self._client = None
                self._init_error = e
        else:
            self._client = None
            self._init_error = None

    def _ensure(self) -> None:
        if not self._client:
            raise RuntimeError("Redis client is not configured")

    def get(self, key: str) -> Optional[Any]:
        self._ensure()
        raw = self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return raw

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._ensure()
        payload = json.dumps(value) if not isinstance(value, (bytes, str)) else value
        return self._client.set(key, payload, ex=ex)

    def incr(self, key: str, amount: int = 1) -> int:
        self._ensure()
        return self._client.incr(key, amount)

    def delete(self, key: str) -> int:
        self._ensure()
        return self._client.delete(key)

# Export a singleton for convenience
redis_client = RedisClient()
