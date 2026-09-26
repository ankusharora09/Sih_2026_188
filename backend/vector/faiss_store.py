"""FAISSVectorStore – minimal placeholder using in‑memory storage.

A real implementation would use the ``faiss`` library for high‑dimensional
similarity search. For the CI environment this stub provides the same API
but delegates to :class:`InMemoryVectorStore`.
"""

from __future__ import annotations

from typing import List, Tuple

from .abstract import VectorStore
from .in_memory import InMemoryVectorStore


class FAISSVectorStore(VectorStore):
    """Placeholder FAISS vector store.

    Stores vectors in memory; suitable for testing when the ``faiss`` package
    is not installed. The public ``add`` and ``query`` methods match the
    contract used by the application.
    """

    def __init__(self) -> None:
        self._inner = InMemoryVectorStore()

    def add(self, id: str, vector: List[float]) -> None:
        self._inner.add(id, vector)

    def query(self, vector: List[float], top_k: int = 10) -> List[Tuple[str, float]]:
        return self._inner.query(vector, top_k)
