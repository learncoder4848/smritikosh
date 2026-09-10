"""Defaults shared across the package."""

from typing import Final

__all__ = ["DEFAULT_DB_PATH", "DEFAULT_MODEL"]

# One file holds vectors, nodes and the incremental caches.
DEFAULT_DB_PATH: Final = "smritikosh.duckdb"

# 67 MB ONNX encoder — 384 dims, 512-token context, CPU-only via fastembed.
# Chosen over jina-embeddings-v2-base-code (768d/8192-token) after measuring
# both on a 365-file repo: identical retrieval quality (MRR 0.947 vs 0.948 on
# 60 docstring->code pairs) at 5.7x the throughput. The 8192-token context
# costs O(n^2) attention for no measurable retrieval benefit on code.
# Also the upstream default of the fastembed library itself.
DEFAULT_MODEL: Final = "BAAI/bge-small-en-v1.5"
