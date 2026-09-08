"""Chunking strategy implementations.

Public surface — import strategies from here, not from sub-modules directly:

    from smritikosh.indexing.strategies import (
        AstChunkingStrategy,
        SectionChunkingStrategy,
        RegexChunkingStrategy,
    )
"""

from smritikosh.indexing.strategies.ast import AstChunkingStrategy
from smritikosh.indexing.strategies.regex import RegexChunkingStrategy
from smritikosh.indexing.strategies.section import SectionChunkingStrategy

__all__ = [
    "AstChunkingStrategy",
    "RegexChunkingStrategy",
    "SectionChunkingStrategy",
]
