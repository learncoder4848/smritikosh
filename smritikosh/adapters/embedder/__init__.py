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
#: Keep in sync with ``make_embedder``.
EMBEDDER_CHOICES: list[str] = ["fastembed"]


def make_embedder(name: str = "fastembed") -> Embedder:
    """Instantiate the :class:`~smritikosh.ports.embedder.Embedder` for *name*.

    *name* is normalised to lowercase so ``"FastEmbed"`` and ``"FASTEMBED"``
    both work.  Only ``fastembed`` (CodeRankEmbed) is currently supported.

    Raises
    ------
    ValueError
        If *name* is not one of :data:`EMBEDDER_CHOICES`.
    """
    name = name.lower()
    if name == "fastembed":
        from smritikosh.adapters.embedder.fastembed import FastEmbedEmbedder

        return FastEmbedEmbedder()
    raise ValueError(
        f"Unknown embedder {name!r}. Choose: {', '.join(EMBEDDER_CHOICES)}."
    )
