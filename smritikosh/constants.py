"""Defaults shared across the package."""

from typing import Final

__all__ = ["DEFAULT_DB_PATH", "DEFAULT_MODEL"]

# One file holds vectors, nodes and the incremental caches.
DEFAULT_DB_PATH: Final = "smritikosh.duckdb"

# 137M code-retrieval bi-encoder — 768 dims, CPU-only via fastembed.
# Purpose-trained on code, so queries phrased as intent ("where do we retry
# failed uploads") land near the implementing code rather than near text that
# merely shares vocabulary. Not in fastembed's catalog; the adapter registers
# it on first use from an INT8 ONNX export (139 MB).
#
# Note: the model card advertises an 8192-token context, but the tokenizer in
# that ONNX export truncates at 512. FastEmbedEmbedder.max_tokens reads the
# tokenizer rather than the card, so chunking respects the real 512 cutoff.
DEFAULT_MODEL: Final = "nomic-ai/CodeRankEmbed"
