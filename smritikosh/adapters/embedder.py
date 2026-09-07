"""Embedding backends -- text in, dense vectors out."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

__all__ = ["DEFAULT_MODEL", "Embedder", "SentenceTransformerEmbedder"]

logger = logging.getLogger(__name__)

DEFAULT_MODEL: Final = "jinaai/jina-code-embeddings-0.5b"


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


class SentenceTransformerEmbedder(Embedder):
    """Local sentence-transformers backend -- no API key, weights cached on disk."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        truncate_dim: int | None = None,
        device: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._truncate_dim = truncate_dim
        self._device = device
        self._model: SentenceTransformer | None = None

    @property
    def dims(self) -> int:
        return self._truncate_dim or self._load().get_embedding_dimension()

    @property
    def model_id(self) -> str:
        return f"{self._model_name}:{self.dims}"

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts, prompt_name="nl2code_document")

    def encode_queries(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts, prompt_name="nl2code_query")

    def _encode(self, texts: list[str], *, prompt_name: str) -> list[list[float]]:
        vectors = self._load().encode(texts, prompt_name=prompt_name)
        return [vector.tolist() for vector in vectors]

    def _load(self) -> SentenceTransformer:
        # Deferred: importing torch costs seconds, and the weights are ~1GB.
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model %s", self._model_name)
            self._model = SentenceTransformer(
                self._model_name,
                device=self._device,
                truncate_dim=self._truncate_dim,
                tokenizer_kwargs={"padding_side": "left"},
            )
        return self._model
