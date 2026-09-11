"""Section-based chunking for document files (Markdown, JSON)."""

from __future__ import annotations

from typing import Final

from smritikosh.engine import sm
from smritikosh.indexing.strategies._helpers import (
    _MIN_CHUNK_CHARS,
    TreeSitterNode,
    build_chunk,
    make_text_chunks,
    split_oversized,
)
from smritikosh.models import Capture, Chunk, ParsedFile

__all__ = ["SectionChunkingStrategy"]

#: Capture names the JSON query emits, shallowest first.  Selection walks this
#: order and stops at the first depth whose capture fits the budget.
_JSON_DEPTHS: Final[tuple[str, ...]] = (
    "definition.section",
    "definition.subsection",
    "definition.subsubsection",
)

#: Comment marker for the key-path line prepended to a JSON chunk.  JSON has no
#: comment syntax, so this is a label for the reader and the embedder rather
#: than something that would round-trip through a parser.
_PATH_MARKER: Final[str] = "// "


def _contains(outer: TreeSitterNode, inner: TreeSitterNode) -> bool:
    """True when *inner*'s byte range sits inside *outer*'s.

    Containment is decided on byte offsets rather than by walking
    ``node.parent`` — the same idiom ``ast.py`` uses for class/init pairing.
    Offsets are all a capture is guaranteed to carry.
    """
    return (
        inner.start_byte >= outer.start_byte
        and inner.end_byte <= outer.end_byte
        # Strictly smaller, so a node never counts as containing itself.
        and (inner.end_byte - inner.start_byte)
        < (outer.end_byte - outer.start_byte)
    )


def _select_by_size(
    captures: list[Capture],
    max_chars: int | None,
) -> list[tuple[Capture, list[Capture]]]:
    """Pick the shallowest captures that fit *max_chars*, with their ancestors.

    Returns ``(capture, ancestors)`` pairs, outermost ancestor first, so a
    caller can build a key path.  A capture within budget is emitted and
    everything nested inside it is skipped; an oversized one is discarded in
    favour of the captures it contains.  Depth is chosen by size, so a small
    config still yields one chunk per top-level key while a large one splits
    along its own key boundaries.

    Descent stops in two cases, both falling back to line-window splitting: a
    capture with no deeper capture inside it, and one whose children are all
    below :data:`_MIN_CHUNK_CHARS` — splitting into fragments that small would
    hurt retrieval more than a coarse chunk does.
    """
    by_depth: list[list[Capture]] = [
        [c for c in captures if c.capture_name == name] for name in _JSON_DEPTHS
    ]
    # Anything the query emitted under an unexpected name still gets chunked.
    extra = [c for c in captures if c.capture_name not in _JSON_DEPTHS]

    selected: list[tuple[Capture, list[Capture]]] = []

    def walk(cap: Capture, depth: int, ancestors: list[Capture]) -> None:
        size = cap.node.end_byte - cap.node.start_byte
        children = (
            [c for c in by_depth[depth + 1] if _contains(cap.node, c.node)]
            if depth + 1 < len(by_depth)
            else []
        )
        if max_chars is None or size <= max_chars or not children:
            selected.append((cap, ancestors))
            return
        # Descending would fragment this section into keys too small to carry
        # meaning; keep the parent whole and let line-windowing split it.
        if all(
            (c.node.end_byte - c.node.start_byte) < _MIN_CHUNK_CHARS for c in children
        ):
            selected.append((cap, ancestors))
            return
        for child in children:
            walk(child, depth + 1, [*ancestors, cap])

    for top in by_depth[0]:
        walk(top, 0, [])
    selected.extend((c, []) for c in extra)
    selected.sort(key=lambda pair: pair[0].node.start_byte)
    return selected


def _key_path(cap: Capture, ancestors: list[Capture]) -> str:
    """Dotted key path for *cap*, e.g. ``chapters.identity.submit_errors``."""
    return ".".join(c.name for c in [*ancestors, cap] if c.name)


def _run_path(run: list[tuple[Capture, list[Capture]]]) -> str:
    """Key path for a run: the single key, or ``parent.a+b`` for merged ones."""
    cap, ancestors = run[0]
    if len(run) == 1:
        return _key_path(cap, ancestors)
    parent = ".".join(a.name for a in ancestors if a.name)
    keys = "+".join(c.name for c, _ in run if c.name)
    return f"{parent}.{keys}" if parent else keys


def _merge_runs(
    selected: list[tuple[Capture, list[Capture]]],
    max_chars: int | None,
) -> list[list[tuple[Capture, list[Capture]]]]:
    """Group adjacent undersized siblings into runs that fit *max_chars*.

    A small config is mostly one-line keys (``"projectKey": "ICCSVC"``), and one
    chunk each retrieves badly — similarity climbs as content shrinks, so those
    fragments crowd out real matches.  Grouping siblings under their shared
    parent path gives each chunk enough context to be worth matching.

    Only same-parent neighbours merge, so a run never spans two unrelated
    subtrees.  A capture already at or above the floor stands alone.
    """
    runs: list[list[tuple[Capture, list[Capture]]]] = []
    for pair in selected:
        cap, ancestors = pair
        size = cap.node.end_byte - cap.node.start_byte
        if runs and size < _MIN_CHUNK_CHARS:
            run = runs[-1]
            last_cap, last_ancestors = run[-1]
            same_parent = [a.name for a in last_ancestors] == [
                a.name for a in ancestors
            ]
            run_size = cap.node.end_byte - run[0][0].node.start_byte
            last_size = last_cap.node.end_byte - last_cap.node.start_byte
            fits = max_chars is None or run_size <= max_chars
            if same_parent and last_size < _MIN_CHUNK_CHARS and fits:
                run.append(pair)
                continue
        runs.append([pair])
    return runs


class SectionChunkingStrategy:
    """One chunk per section capture, sized to the embedder's window.

    Markdown sections are emitted as-is: a heading is already natural language,
    so it needs no extra label.

    JSON is different, in three ways:

    * **Depth by size.** The query captures three nesting levels and selection
      takes the shallowest that *fits* (:func:`_select_by_size`), so chunks
      align with key boundaries rather than arbitrary lines.
    * **Runs.** Adjacent undersized siblings merge into one chunk
      (:func:`_merge_runs`), labelled ``parent.a+b`` — a config of one-line
      keys would otherwise become chunks too small to retrieve.
    * **Key paths.** Each JSON chunk is prefixed with its dotted path, because
      a mid-file JSON fragment is otherwise unidentifiable to a reader and to
      the embedder alike.  The prefix is part of ``text``, so it is both
      embedded and shown as the search snippet; ``start_line`` still points at
      the captured value, so the printed range covers one line fewer than the
      printed snippet.
    """

    mode_name = "section"

    def __init__(self, max_chars: int | None = None) -> None:
        self.max_chars = max_chars

    @sm.tracked
    def chunk(self, parsed: ParsedFile, captures: list[Capture]) -> list[Chunk]:
        if not captures:
            lines = parsed.content.splitlines()
            return make_text_chunks(
                parsed,
                parsed.content,
                "section",
                1,
                max(len(lines), 1),
                self.max_chars,
            )

        label = parsed.language == "json"
        raw = parsed.content.encode()
        selected = _select_by_size(captures, self.max_chars if label else None)
        groups = (
            _merge_runs(selected, self.max_chars)
            if label
            else [[pair] for pair in selected]
        )
        chunks: list[Chunk] = []
        for run in groups:
            cap, ancestors = run[0]
            last_node = run[-1][0].node
            # A run spans from its first capture to its last, so the text
            # between merged siblings (commas, newlines) travels with them.
            body = raw[cap.node.start_byte : last_node.end_byte].decode()
            first_line = cap.node.start_point[0] + 1
            path = _run_path(run) if label else ""
            if not path:
                chunks.extend(
                    make_text_chunks(
                        parsed,
                        body,
                        "section",
                        first_line,
                        last_node.end_point[0] + 1,
                        self.max_chars,
                    )
                )
                continue

            # Split the body first, then label each window.  Prefixing before
            # the split would make the prefix its own line, so the splitter
            # could peel it off into a 4-char chunk and leave the body
            # unlabelled — the exact degenerate fragment this work removes.
            prefix = f"{_PATH_MARKER}{path}\n"
            budget = (
                None
                if self.max_chars is None
                else max(self.max_chars - len(prefix), 1)
            )
            windows = (
                split_oversized(body, budget) if budget is not None else [(body, 0, 0)]
            )
            for piece, first, last in windows:
                chunks.append(
                    build_chunk(
                        parsed.path,
                        prefix + piece,
                        "section",
                        first_line + first,
                        first_line + last,
                    )
                )
        return chunks
