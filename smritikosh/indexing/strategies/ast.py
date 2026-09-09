"""AST-based chunking for code files (Python, Java, Kotlin, TypeScript, JS)."""

from __future__ import annotations

from collections import defaultdict
from typing import Final, Literal

from smritikosh.engine import sm
from smritikosh.indexing.strategies._helpers import (
    TreeSitterNode,
    make_group_chunk,
    make_node_chunk,
    make_text_chunk,
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


@sm.tracked  # source hash in _tracked_logic_fps — change here busts process_file memo
def _deduplicate_by_priority(
    captures: list[Capture],
    priority: dict[str, int],
) -> list[Capture]:
    """Keep the highest-priority capture per node.id, sorted by start_byte."""
    best: dict[int, Capture] = {}
    for cap in captures:
        node_id = cap.node.id
        current_pri = priority.get(cap.capture_name, 0)
        if node_id not in best:
            best[node_id] = cap
        elif current_pri > priority.get(best[node_id].capture_name, 0):
            best[node_id] = cap
    return sorted(best.values(), key=lambda c: c.node.start_byte)


@sm.tracked  # source hash in _tracked_logic_fps — change here busts process_file memo
def _find_class_init(
    captures: list[Capture],
    class_node: TreeSitterNode,
    skip: set[int],
) -> Capture | None:
    """Return the first class_init capture whose node is inside *class_node*."""
    for cap in captures:
        if (
            cap.capture_name == "definition.class_init"
            and cap.node.id not in skip
            and cap.node.start_byte >= class_node.start_byte
            and cap.node.end_byte <= class_node.end_byte
        ):
            return cap
    return None


@sm.tracked  # source hash in _tracked_logic_fps — change here busts process_file memo
def _apply_grouping(
    parsed: ParsedFile,
    captures: list[Capture],
    grouping: dict[str, Action],
) -> list[Chunk]:
    """Dispatch captures to group/whole/with_init/own/skip actions.

    *captures* must already be deduplicated (one per node.id) — call
    _deduplicate_by_priority first. Passing raw captures can produce duplicate
    chunks for nodes that match multiple capture names.
    """
    chunks: list[Chunk] = []
    skip: set[int] = set()
    group_buckets: dict[str, list[TreeSitterNode]] = defaultdict(list)
    raw = parsed.content.encode()

    for cap in captures:
        if cap.node.id in skip:
            continue
        action = grouping.get(cap.capture_name, "own")

        if action == "skip":
            skip.add(cap.node.id)

        elif action == "group":
            group_buckets[cap.capture_name].append(cap.node)
            skip.add(cap.node.id)

        elif action in ("whole", "own"):
            kind = cap.capture_name.split(".")[-1]
            chunks.append(make_node_chunk(parsed, cap.node, kind, raw))
            skip.add(cap.node.id)

        elif action == "with_init":
            init_cap = _find_class_init(captures, cap.node, skip)
            kind = cap.capture_name.split(".")[-1]
            if init_cap:
                skip.add(init_cap.node.id)
                start_byte = min(cap.node.start_byte, init_cap.node.start_byte)
                end_byte = max(cap.node.end_byte, init_cap.node.end_byte)
                text = raw[start_byte:end_byte].decode()
                start_line = (
                    min(cap.node.start_point[0], init_cap.node.start_point[0]) + 1
                )
                end_line = max(cap.node.end_point[0], init_cap.node.end_point[0]) + 1
                chunks.append(make_text_chunk(parsed, text, kind, start_line, end_line))
            else:
                chunks.append(make_node_chunk(parsed, cap.node, kind, raw))
            skip.add(cap.node.id)

    for capture_name, nodes in group_buckets.items():
        chunks.append(make_group_chunk(parsed, nodes, capture_name.split(".")[-1], raw))

    return chunks


class AstChunkingStrategy:
    """Chunk code files using tree-sitter AST captures."""

    mode_name = "ast"

    @sm.tracked
    def chunk(self, parsed: ParsedFile, captures: list[Capture]) -> list[Chunk]:
        deduped = _deduplicate_by_priority(captures, CAPTURE_PRIORITY)
        return _apply_grouping(parsed, deduped, CHUNK_GROUPING)
