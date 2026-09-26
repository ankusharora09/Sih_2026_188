"""Vector store factory.

Selects a concrete implementation based on the VECTOR_BACKEND setting.
Falls back to InMemoryVectorStore if the selected backend is unavailable.
"""

from __future__ import annotations

from ..config import settings

from .abstract import VectorStore
from .in_memory import InMemoryVectorStore


def get_vector_store() -> VectorStore:
    backend = (settings.VECTOR_BACKEND or "memory").lower()
    if backend == "faiss":
        try:
            from .faiss_store import FAISSVectorStore
            return FAISSVectorStore()
        except Exception:
            pass
    if backend == "pgvector":
        try:
            from .pgvector_store import PGVectorStore
            return PGVectorStore()
        except Exception:
            pass
    # Default fallback
    return InMemoryVectorStore()
