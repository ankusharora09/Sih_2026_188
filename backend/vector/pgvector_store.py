"""PGVectorStore – minimal placeholder using in‑memory storage.

In a real deployment this would interface with the PostgreSQL ``pgvector``
extension. For the purposes of this repository (and the test suite) we provide
a thin wrapper that internally delegates to :class:`InMemoryVectorStore`.
This satisfies the ``VectorStore`` interface and allows the ``get_vector_store``
factory to instantiate a ``pgvector`` backend without requiring external
dependencies.
"""

from __future__ import annotations

from typing import List, Tuple

from .abstract import VectorStore
from .in_memory import InMemoryVectorStore


class PGVectorStore(VectorStore):
    """Placeholder implementation for a PostgreSQL vector store.

    The class mirrors the public API of a real pgvector store, but stores all
    vectors in a local ``dict``. This is sufficient for unit tests and for the
    CI environment where PostgreSQL with pgvector may not be available.
    """

    def __init__(self) -> None:
        self._inner = InMemoryVectorStore()

    def add(self, id: str, vector: List[float]) -> None:
        self._inner.add(id, vector)

    def query(self, vector: List[float], top_k: int = 10) -> List[Tuple[str, float]]:
        return self._inner.query(vector, top_k)
