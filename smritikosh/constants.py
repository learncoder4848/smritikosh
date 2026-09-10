"""Defaults shared across the package."""

from typing import Final

__all__ = ["DEFAULT_DB_PATH", "DEFAULT_MODEL"]

# One file holds vectors, nodes and the incremental caches.
DEFAULT_DB_PATH: Final = "smritikosh.duckdb"

# Jina's code model as a quantised ONNX file — 0.64 GB, 768 dims,
# 30 programming languages, 8192-token context, CPU-only via fastembed.
DEFAULT_MODEL: Final = "jinaai/jina-embeddings-v2-base-code"
