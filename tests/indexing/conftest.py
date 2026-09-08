"""Shared test doubles for all indexing strategy tests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from smritikosh.models import Capture, ParsedFile

# ── FakeNode ──────────────────────────────────────────────────────────────

_id_counter = 0


def _next_id() -> int:
    global _id_counter
    _id_counter += 1
    return _id_counter


@dataclass
class FakeNode:
    """Minimal tree-sitter node double for unit tests."""

    start_byte: int
    end_byte: int
    start_point: tuple[int, int]  # (row, col) 0-indexed
    end_point: tuple[int, int]
    id: int = field(default_factory=_next_id)


# ── Builder helpers ────────────────────────────────────────────────────────


def node_for(content: str, text: str, node_id: int | None = None) -> FakeNode:
    """Return a FakeNode whose byte range exactly covers *text* in *content*."""
    enc = content.encode()
    text_enc = text.encode()
    pos = enc.find(text_enc)
    assert pos != -1, f"{text!r} not found in content"
    start_row = content[:pos].count("\n")
    end_row = content[: pos + len(text)].count("\n")
    n = FakeNode(
        start_byte=pos,
        end_byte=pos + len(text_enc),
        start_point=(start_row, 0),
        end_point=(end_row, 0),
    )
    if node_id is not None:
        n.id = node_id
    return n


def parsed(content: str, path: str = "test.py") -> ParsedFile:
    """Return a ParsedFile wrapping *content*."""
    return ParsedFile(path=path, language="python", content=content, tree=None)


def cap(name: str, node: FakeNode, path: str = "test.py") -> Capture:
    """Return a Capture for *node* with the given capture *name*."""
    return Capture(capture_name=name, node=node, name="", path=path)


def cid(text: str) -> str:
    """Return the expected chunk id for *text*."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]
