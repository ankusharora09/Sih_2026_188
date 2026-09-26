"""Abstract base class for vector stores.

Implementations must provide add(id, vector) and query(vector, top_k).
"""

from __future__ import annotations

from typing import List, Tuple, Any


class VectorStore:
    def add(self, id: str, vector: Any) -> None:
        raise NotImplementedError

    def query(self, vector: Any, top_k: int = 10) -> List[Tuple[str, float]]:
        """Return a list of (id, similarity) sorted by descending similarity.
        """
        raise NotImplementedError
