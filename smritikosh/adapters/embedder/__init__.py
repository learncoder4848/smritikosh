"""smritikosh.adapters.embedder — embedder adapters and factory.

Public API
----------
All symbols are importable directly from ``smritikosh.adapters.embedder``::

    from smritikosh.adapters.embedder import make_embedder, EMBEDDER_CHOICES

``FastEmbedEmbedder`` is also importable from its own submodule::

    from smritikosh.adapters.embedder.fastembed import FastEmbedEmbedder
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from smritikosh.ports.embedder import Embedder

__all__ = ["EMBEDDER_CHOICES", "make_embedder"]

#: Canonical list of supported embedder names.
#: Imported by the CLI to build ``click.Choice``; keep in sync with ``make_embedder``.
EMBEDDER_CHOICES: list[str] = ["fastembed", "voyage", "openai"]


def make_embedder(name: str, *, model: str | None = None) -> Embedder:
    """Instantiate the :class:`~smritikosh.ports.embedder.Embedder` for *name*.

    *name* is normalised to lowercase so ``"FastEmbed"`` and ``"FASTEMBED"``
    both work.

    Parameters
    ----------
    name:
        One of :data:`EMBEDDER_CHOICES`.
    model:
        For the ``fastembed`` backend only — any model listed by
        ``TextEmbedding.list_supported_models()``.  ``None`` uses
        :data:`~smritikosh.constants.DEFAULT_MODEL`.

    Raises
    ------
    ImportError
        If the requested adapter's optional package is not installed.
    ValueError
        If *name* is not one of :data:`EMBEDDER_CHOICES`.
    """
    name = name.lower()
    if name == "fastembed":
        from smritikosh.adapters.embedder.fastembed import FastEmbedEmbedder

        return FastEmbedEmbedder(model) if model else FastEmbedEmbedder()
    if name == "voyage":
        try:
            from smritikosh.adapters.embedder.voyage import (
                VoyageCodeEmbedder,  # type: ignore[import]
            )
        except ImportError as exc:
            raise ImportError(
                "Voyage embedder is not available. "
                "Install the smritikosh voyage adapter to continue."
            ) from exc
        return VoyageCodeEmbedder()
    if name == "openai":
        try:
            from smritikosh.adapters.embedder.openai import (
                OpenAIEmbedder,  # type: ignore[import]
            )
        except ImportError as exc:
            raise ImportError(
                "OpenAI embedder is not available. "
                "Install the smritikosh openai adapter to continue."
            ) from exc
        return OpenAIEmbedder()
    raise ValueError(
        f"Unknown embedder {name!r}. Choose: {', '.join(EMBEDDER_CHOICES)}."
    )
