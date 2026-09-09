"""Chunking strategy implementations.

Public surface — import strategies from here, not from sub-modules directly:

    from smritikosh.indexing.strategies import (
        ChunkingStrategy,
        AstChunkingStrategy,
        SectionChunkingStrategy,
        RegexChunkingStrategy,
    )
"""

from smritikosh.indexing.strategies.ast import AstChunkingStrategy
from smritikosh.indexing.strategies.regex import RegexChunkingStrategy
from smritikosh.indexing.strategies.section import SectionChunkingStrategy
from smritikosh.models import (
    ChunkingStrategy,  # re-export: contract co-located with its implementations
)

__all__ = [
    "AstChunkingStrategy",
    "ChunkingStrategy",
    "RegexChunkingStrategy",
    "SectionChunkingStrategy",
]
