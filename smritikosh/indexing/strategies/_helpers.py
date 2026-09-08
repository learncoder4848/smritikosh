"""Shared chunk-building helpers for the strategies package."""

from __future__ import annotations

import hashlib
from typing import Any

from smritikosh.models import Chunk, ParsedFile

# Tree-sitter has no Python stubs.
TreeSitterNode = Any


def chunk_id(text: str) -> str:
    """sha256(text)[:16] — stable, content-addressed chunk id."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def content_hash(text: str) -> str:
    """Full SHA-256 hex digest of *text*."""
    return hashlib.sha256(text.encode()).hexdigest()


def extract_node_text(parsed: ParsedFile, node: TreeSitterNode) -> str:
    """Extract node text from *parsed.content* using byte offsets."""
    return parsed.content.encode()[node.start_byte : node.end_byte].decode()


def make_node_chunk(
    parsed: ParsedFile, node: TreeSitterNode, chunk_kind: str
) -> Chunk:
    """Build a Chunk from a single tree-sitter node."""
    text = extract_node_text(parsed, node)
    return Chunk(
        id=chunk_id(text),
        path=parsed.path,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        text=text,
        chunk_kind=chunk_kind,
        content_hash=content_hash(text),
    )


def make_group_chunk(
    parsed: ParsedFile, nodes: list[TreeSitterNode], chunk_kind: str
) -> Chunk:
    """Build a Chunk by concatenating *nodes* (newline-separated)."""
    texts = [extract_node_text(parsed, n) for n in nodes]
    text = "\n".join(texts)
    return Chunk(
        id=chunk_id(text),
        path=parsed.path,
        start_line=min(n.start_point[0] + 1 for n in nodes),
        end_line=max(n.end_point[0] + 1 for n in nodes),
        text=text,
        chunk_kind=chunk_kind,
        content_hash=content_hash(text),
    )


def make_text_chunk(
    parsed: ParsedFile,
    text: str,
    chunk_kind: str,
    start_line: int,
    end_line: int,
) -> Chunk:
    """Build a Chunk from a pre-extracted text string."""
    return Chunk(
        id=chunk_id(text),
        path=parsed.path,
        start_line=start_line,
        end_line=end_line,
        text=text,
        chunk_kind=chunk_kind,
        content_hash=content_hash(text),
    )
