"""In‑memory vector store implementation – simple cosine similarity.

Used as the default fallback when no external vector backend is configured.
"""

from __future__ import annotations

import math
from typing import List, Tuple, Dict

from .abstract import VectorStore


def _cosine(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class InMemoryVectorStore(VectorStore):
    def __init__(self) -> None:
        self._vectors: Dict[str, List[float]] = {}

    def add(self, id: str, vector: List[float]) -> None:
        self._vectors[id] = vector

    def query(self, vector: List[float], top_k: int = 10) -> List[Tuple[str, float]]:
        scores = [(id, _cosine(vector, vec)) for id, vec in self._vectors.items()]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
