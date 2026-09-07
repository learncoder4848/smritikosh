"""Shared data types passed between pipeline stages."""

from dataclasses import dataclass, field


@dataclass
class SourceFile:
    path: str
    language: str
    content: str


@dataclass
class ParsedFile:
    path: str
    language: str
    tree: object  # tree-sitter AST (or your chosen representation)


@dataclass
class Symbol:
    name: str
    kind: str  # e.g. function, class, variable
    path: str
    start_line: int
    end_line: int


@dataclass
class Chunk:
    id: str
    path: str
    start_line: int
    end_line: int
    text: str
    symbol: str | None = None


@dataclass
class EmbeddedChunk:
    chunk: Chunk
    vector: list[float]


@dataclass
class SearchResult:
    path: str
    start_line: int
    end_line: int
    snippet: str
    score: float
    source: str = ""
    metadata: dict = field(default_factory=dict)
