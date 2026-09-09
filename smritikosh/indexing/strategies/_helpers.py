"""Shared chunk-building helpers for the strategies package."""

from __future__ import annotations

import hashlib
from typing import Any

from smritikosh.engine import sm
from smritikosh.models import Chunk, ParsedFile

TreeSitterNode = Any


def chunk_id(text: str) -> str:
    """sha256(text)[:16] — stable, content-addressed chunk id."""
    return content_hash(text)[:16]


def content_hash(text: str) -> str:
    """Full SHA-256 hex digest of *text*."""
    return hashlib.sha256(text.encode()).hexdigest()


def extract_node_text(
    parsed: ParsedFile,
    node: TreeSitterNode,
    content_bytes: bytes | None = None,
) -> str:
    """Extract node text using byte offsets. Pass *content_bytes* to encode once."""
    raw = content_bytes if content_bytes is not None else parsed.content.encode()
    return raw[node.start_byte : node.end_byte].decode()


@sm.tracked
def build_chunk(
    path: str,
    text: str,
    chunk_kind: str,
    start_line: int,
    end_line: int,
) -> Chunk:
    """Build a content-addressed Chunk. id is sha256(text)[:16]."""
    digest = content_hash(text)
    return Chunk(
        id=digest[:16],
        path=path,
        start_line=start_line,
        end_line=end_line,
        text=text,
        chunk_kind=chunk_kind,
        content_hash=digest,
    )


def make_node_chunk(
    parsed: ParsedFile,
    node: TreeSitterNode,
    chunk_kind: str,
    content_bytes: bytes | None = None,
) -> Chunk:
    """Build a Chunk from a single tree-sitter node."""
    text = extract_node_text(parsed, node, content_bytes)
    return build_chunk(
        parsed.path,
        text,
        chunk_kind,
        node.start_point[0] + 1,
        node.end_point[0] + 1,
    )


def make_group_chunk(
    parsed: ParsedFile,
    nodes: list[TreeSitterNode],
    chunk_kind: str,
    content_bytes: bytes | None = None,
) -> Chunk:
    """Build a Chunk by concatenating *nodes* (newline-separated)."""
    raw = content_bytes if content_bytes is not None else parsed.content.encode()
    texts = [extract_node_text(parsed, n, raw) for n in nodes]
    return build_chunk(
        parsed.path,
        "\n".join(texts),
        chunk_kind,
        min(n.start_point[0] + 1 for n in nodes),
        max(n.end_point[0] + 1 for n in nodes),
    )


def make_text_chunk(
    parsed: ParsedFile,
    text: str,
    chunk_kind: str,
    start_line: int,
    end_line: int,
) -> Chunk:
    """Build a Chunk from a pre-extracted text string."""
    return build_chunk(parsed.path, text, chunk_kind, start_line, end_line)
