"""The vector storage contract -- implementations live in adapters/vector_store/."""

from __future__ import annotations

from abc import ABC, abstractmethod

__all__ = ["VectorStore"]


class VectorStore(ABC):
    """Stores one vector per chunk and ranks them against a query vector."""

    @abstractmethod
    def setup(self, dims: int) -> None:
        """Prepare storage for vectors of width dims, rebuilding if dims changed."""

    @abstractmethod
    def upsert(self, chunk_id: str, vector: list[float]) -> None: ...

    @abstractmethod
    def search(self, query_vector: list[float], top_k: int) -> list[tuple[str, float]]:
        """Return (chunk_id, cosine_score) pairs ranked by score descending."""

    @abstractmethod
    def delete(self, chunk_id: str) -> None: ...

    @abstractmethod
    def exists(self, chunk_id: str) -> bool: ...

    @abstractmethod
    def get_stored_dims(self) -> int | None:
        """Width the store was last set up with, or None if never set up."""
