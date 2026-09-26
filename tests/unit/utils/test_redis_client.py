import os
import pytest

from backend.utils.redis_client import RedisClient

def test_redis_client_without_url_raises():
    # Ensure REDIS_URL is not set
    os.environ.pop("REDIS_URL", None)
    client = RedisClient()
    assert client._client is None
    with pytest.raises(RuntimeError):
        client.get("somekey")
    with pytest.raises(RuntimeError):
        client.set("somekey", "value")
    with pytest.raises(RuntimeError):
        client.incr("counter")
    with pytest.raises(RuntimeError):
        client.delete("somekey")
