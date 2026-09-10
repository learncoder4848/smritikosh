"""smritikosh.adapters.embedder — embedder adapters and factory.

Public API
----------
All symbols are importable directly from ``smritikosh.adapters.embedder``::

    from smritikosh.adapters.embedder import make_embedder, EMBEDDER_CHOICES

``SentenceTransformerEmbedder`` is also importable from its own submodule::

    from smritikosh.adapters.embedder.sentence_transformer import (
        SentenceTransformerEmbedder,
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from smritikosh.ports.embedder import Embedder

__all__ = ["EMBEDDER_CHOICES", "make_embedder"]

#: Canonical list of supported embedder names.
#: Imported by the CLI to build ``click.Choice``; keep in sync with ``make_embedder``.
EMBEDDER_CHOICES: list[str] = ["jina"]


def make_embedder(name: str) -> Embedder:
    """Instantiate the :class:`~smritikosh.ports.embedder.Embedder` for *name*.

    *name* is normalised to lowercase so ``"Jina"`` and ``"JINA"`` both work.

    Raises
    ------
    ValueError
        If *name* is not one of :data:`EMBEDDER_CHOICES`.
    """
    name = name.lower()
    if name == "jina":
        from smritikosh.adapters.embedder.sentence_transformer import (
            SentenceTransformerEmbedder,
        )

        return SentenceTransformerEmbedder()
    raise ValueError(
        f"Unknown embedder {name!r}. Choose: {', '.join(EMBEDDER_CHOICES)}."
    )
