"""Tampering detection package – simple implementation for demo purposes.
"""

from functools import lru_cache

from .adapter import TamperingDetectionAdapter
from .simple_tampering_adapter import SimpleTamperingAdapter


@lru_cache(maxsize=1)
def get_verifier() -> TamperingDetectionAdapter:
    """Factory returning the (cached) default simple tampering detector."""
    return SimpleTamperingAdapter()
