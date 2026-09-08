"""AST-based chunking for code files (Python, Java, Kotlin, TypeScript, JS)."""

from __future__ import annotations

from collections import defaultdict
from typing import Final, Literal

from smritikosh.indexing.strategies._helpers import (
    TreeSitterNode,
    make_group_chunk,
    make_node_chunk,
)
from smritikosh.models import Capture, Chunk, ParsedFile

__all__ = ["AstChunkingStrategy", "CAPTURE_PRIORITY", "CHUNK_GROUPING"]

Action = Literal["group", "own", "skip", "whole", "with_init"]

# Higher priority wins when two captures share the same node.
CAPTURE_PRIORITY: Final[dict[str, int]] = {
    "definition.class_init": 10,
    "definition.enum": 9,
    "definition.class_constant": 8,
    "definition.constant": 7,
    "definition.class": 6,
    "definition.interface": 6,
    "definition.module": 6,
    "definition.function": 5,
    "definition.method": 5,
    "definition.type": 4,
}

CHUNK_GROUPING: Final[dict[str, Action]] = {
    "definition.constant": "group",
    "definition.class_constant": "group",
    "definition.enum": "whole",
    "definition.class": "with_init",
    "definition.class_init": "skip",
    "definition.function": "own",
    "definition.method": "own",
    "definition.interface": "whole",
    "definition.module": "whole",
    "definition.type": "own",
}


def _deduplicate_by_priority(
    captures: list[Capture],
    priority: dict[str, int],
) -> list[Capture]:
    """Return one capture per node.id, keeping the highest-priority capture."""
    best: dict[int, Capture] = {}
    for cap in captures:
        node_id = cap.node.id
        current_pri = priority.get(cap.capture_name, 0)
        if node_id not in best:
            best[node_id] = cap
        elif current_pri > priority.get(best[node_id].capture_name, 0):
            best[node_id] = cap
    return list(best.values())


def _find_class_init(
    captures: list[Capture],
    class_node: TreeSitterNode,
    skip: set[int],
) -> Capture | None:
    """Return the first class_init capture contained within *class_node*."""
    for cap in captures:
        if (
            cap.capture_name == "definition.class_init"
            and id(cap) not in skip
            and cap.node.start_byte >= class_node.start_byte
            and cap.node.end_byte <= class_node.end_byte
        ):
            return cap
    return None


def _apply_grouping(
    parsed: ParsedFile,
    captures: list[Capture],
    grouping: dict[str, Action],
) -> list[Chunk]:
    """Dispatch captures to their grouping actions and return the resulting chunks."""
    chunks: list[Chunk] = []
    group_buckets: dict[str, list[TreeSitterNode]] = defaultdict(list)
    used_inits: set[int] = set()

    for cap in captures:
        action: Action = grouping.get(cap.capture_name, "own")  # type: ignore[assignment]

        if action == "skip":
            pass

        elif action == "group":
            group_buckets[cap.capture_name].append(cap.node)

        elif action in ("whole", "own"):
            kind = cap.capture_name.split(".")[-1]
            chunks.append(make_node_chunk(parsed, cap.node, kind))

        elif action == "with_init":
            init_cap = _find_class_init(captures, cap.node, used_inits)
            if init_cap:
                used_inits.add(id(init_cap))
                chunk = make_group_chunk(parsed, [cap.node, init_cap.node], "class")
            else:
                chunk = make_node_chunk(parsed, cap.node, "class")
            chunks.append(chunk)

    for capture_name, nodes in group_buckets.items():
        chunks.append(make_group_chunk(parsed, nodes, capture_name.split(".")[-1]))

    return chunks


class AstChunkingStrategy:
    """Chunk code files using tree-sitter AST captures."""

    mode_name = "ast"

    def chunk(self, parsed: ParsedFile, captures: list[Capture]) -> list[Chunk]:
        deduped = _deduplicate_by_priority(captures, CAPTURE_PRIORITY)
        return _apply_grouping(parsed, deduped, CHUNK_GROUPING)
