"""Defaults shared across the package."""

from typing import Final

__all__ = ["DEFAULT_DB_PATH", "DEFAULT_MODEL"]

# One file holds vectors, nodes and the incremental caches.
DEFAULT_DB_PATH: Final = "smritikosh.duckdb"

DEFAULT_MODEL: Final = "jinaai/jina-code-embeddings-1.5b"
