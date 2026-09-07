"""Local embedding backend -- no API key, weights cached on disk."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

from smritikosh.ports.embedder import Embedder

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

__all__ = ["DEFAULT_MODEL", "SentenceTransformerEmbedder"]

logger = logging.getLogger(__name__)

DEFAULT_MODEL: Final = "jinaai/jina-code-embeddings-0.5b"


class SentenceTransformerEmbedder(Embedder):
    """Embeds through a local sentence-transformers model."""

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
