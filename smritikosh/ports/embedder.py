"""The embedding contract -- implementations live in adapters/embedder/."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

__all__ = ["Embedder"]


class Embedder(ABC):
    """Turns text into dense vectors for indexing and search."""

    @property
    @abstractmethod
    def dims(self) -> int:
        """Vector width, which drives VectorStore.setup()."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Model identity; a change invalidates every cached embedding."""

    @abstractmethod
    def encode_documents(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def encode_queries(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_document(self, text: str) -> list[float]:
        vectors = await asyncio.to_thread(self.encode_documents, [text])
        return vectors[0]

    async def embed_query(self, text: str) -> list[float]:
        vectors = await asyncio.to_thread(self.encode_queries, [text])
        return vectors[0]

    async def embed_documents_batch(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(self.encode_documents, texts)
