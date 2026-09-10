"""Local embedding backend — fastembed + ONNX Runtime, no PyTorch, CPU-only.

Any model listed by ``TextEmbedding.list_supported_models()`` is accepted.
The default (``jinaai/jina-embeddings-v2-base-code``) is code-specific:
30 programming languages, 8 192-token context, 768 dims, 0.64 GB on disk.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from smritikosh.constants import DEFAULT_MODEL
from smritikosh.ports.embedder import Embedder

if TYPE_CHECKING:
    from fastembed import TextEmbedding

__all__ = ["FastEmbedEmbedder"]

logger = logging.getLogger(__name__)


class FastEmbedEmbedder(Embedder):
    """Embeds via fastembed + ONNX Runtime — no PyTorch, runs on any CPU.

    Parameters
    ----------
    model_name:
        Any model from ``TextEmbedding.list_supported_models()``.
        Defaults to :data:`~smritikosh.constants.DEFAULT_MODEL`.
    threads:
        Number of ONNX intra-op threads.  ``None`` lets ONNX Runtime
        choose (usually one thread per physical core).
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        threads: int | None = None,
    ) -> None:
        self._model_name = model_name
        self._threads = threads
        self._model: TextEmbedding | None = None

    # ── Embedder protocol ─────────────────────────────────────────────────────

    @property
    def dims(self) -> int:
        # embedding_size is resolved from the model registry without a forward
        # pass — no dummy text needed.
        return self._load().embedding_size

    @property
    def model_id(self) -> str:
        return f"{self._model_name}:{self.dims}"

    def encode_documents(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._load().embed(texts)]

    def encode_queries(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._load().query_embed(texts)]

    # ── Pickle support ────────────────────────────────────────────────────────
    # The engine's change-detection fingerprinting calls pickle.dumps(embedder).
    # onnxruntime.InferenceSession (held inside TextEmbedding) is not picklable,
    # so we exclude it.  _load() recreates the session lazily after unpickling.

    def __getstate__(self) -> dict:
        return {"_model_name": self._model_name, "_threads": self._threads, "_model": None}

    def __setstate__(self, state: dict) -> None:
        self.__dict__.update(state)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load(self) -> TextEmbedding:
        """Lazy-load the ONNX model on first call."""
        if self._model is None:
            import truststore
            from fastembed import TextEmbedding

            # Corporate proxies (Zscaler etc.) MITM TLS; inject the OS trust
            # store so model downloads succeed without extra CA bundles.
            truststore.inject_into_ssl()

            logger.info("Loading fastembed model %s", self._model_name)
            self._model = TextEmbedding(
                self._model_name,
                threads=self._threads,
            )
        return self._model
