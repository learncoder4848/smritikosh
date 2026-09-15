"""Turn tree-sitter captures into graph symbols and unresolved references.

Definitions become :class:`~smritikosh.models.Symbol` rows. Every name a file
mentions becomes a :class:`~smritikosh.models.Reference` row carrying the text
as written, never a pointer to whatever it might mean — that lookup needs every
file in the repository and so runs once, after indexing.

Nothing here reaches the embedder: a reference is a pointer, not a concept, and
only the symbols at each end of an edge carry meaning worth a vector.
"""

from __future__ import annotations

import hashlib
from typing import Final

from smritikosh.engine import sm
from smritikosh.models import Capture, ParsedFile, Reference, Symbol

__all__ = ["graph_file", "name_tail"]

#: Names that no repository symbol will ever satisfy. Dropping them at
#: extraction is a local, static decision — it needs no knowledge of what the
#: rest of the repository defines — and removes the single largest block of
#: references that could only ever resolve to nothing.
_UNRESOLVABLE_NAMES: Final[frozenset[str]] = frozenset(
    """
    abs all any bool bytes callable chr dict dir enumerate filter float format
    frozenset getattr hasattr hash hex id input int isinstance issubclass iter
    len list map max min next object oct open ord print range repr reversed
    round set setattr slice sorted str sum super tuple type vars zip
    append extend insert remove pop clear copy get items keys values update
    join split strip lstrip rstrip replace startswith endswith lower upper
    encode decode read write close add discard sort index count
    """.split()
)

#: Separators a qualified reference can use. ``::`` is checked before ``.`` only
#: in the sense that both are scanned; the rightmost of either wins.
_NAME_SEPARATORS: Final[tuple[str, ...]] = (".", "::")


def name_tail(name: str) -> str:
    """Return the last segment of a possibly qualified name.

    A definition writes its own bare name — ``def validate`` — while a caller
    writes a qualified one — ``billing.validate``. Matching on the tail is what
    lets the two halves meet.

    Args:
        name: Reference name as written in the source.

    Returns:
        The segment after the final separator, or *name* when it has none.
    """
    # Each separator contributes the index *past* itself, so a two-character
    # separator does not leave half of itself on the front of the tail.
    cut: int = -1
    for separator in _NAME_SEPARATORS:
        found: int = name.rfind(separator)
        if found >= 0:
            cut = max(cut, found + len(separator))
    return name[cut:] if cut >= 0 else name


@sm.tracked  # source hash in _tracked_logic_fps — change here busts process_file memo
def graph_file(
    parsed: ParsedFile,
    definitions: list[Capture],
    references: list[Capture],
) -> tuple[list[Symbol], list[Reference]]:
    """Build the symbols and unresolved references for one parsed file.

    Args:
        parsed: The parsed source file.
        definitions: ``definition.*`` captures, as the chunker receives them.
        references: ``reference.*`` captures.

    Returns:
        The file's symbols, and the references each of them makes. A mention
        that sits outside every definition — a module-level call — belongs to
        no symbol and is dropped.
    """
    symbols: list[Symbol] = _to_symbols(parsed, definitions)
    return symbols, _to_references(parsed, references, symbols)


def _to_symbols(parsed: ParsedFile, definitions: list[Capture]) -> list[Symbol]:
    """Convert definition captures into symbols, innermost parent attached."""
    spans: list[tuple[Capture, int, int]] = [
        (capture, capture.node.start_point[0] + 1, capture.node.end_point[0] + 1)
        for capture in definitions
    ]
    symbols: list[Symbol] = []
    for capture, start_line, end_line in spans:
        kind: str = capture.capture_name.removeprefix("definition.")
        symbols.append(
            Symbol(
                id=symbol_id(parsed.path, capture.name, start_line),
                name=capture.name,
                kind=kind,
                path=parsed.path,
                start_line=start_line,
                end_line=end_line,
                parent=None,
            )
        )
    return symbols


def _to_references(
    parsed: ParsedFile,
    references: list[Capture],
    symbols: list[Symbol],
) -> list[Reference]:
    """Attach each mention to the innermost symbol whose lines contain it."""
    result: list[Reference] = []
    for capture in references:
        if name_tail(capture.name) in _UNRESOLVABLE_NAMES:
            continue
        line: int = capture.node.start_point[0] + 1
        owner: Symbol | None = _innermost_containing(symbols, line)
        if owner is None:
            continue
        kind: str = capture.capture_name.removeprefix("reference.")
        result.append(
            Reference(
                id=reference_id(
                    owner.id, capture.name, line, capture.node.start_point[1]
                ),
                src_symbol=owner.id,
                name=capture.name,
                kind=kind,
                path=parsed.path,
                line=line,
            )
        )
    return result


def _innermost_containing(symbols: list[Symbol], line: int) -> Symbol | None:
    """Return the narrowest symbol spanning *line*.

    A method sits inside its class, and both contain the call; the method is
    the honest answer to "who made this call".
    """
    best: Symbol | None = None
    for symbol in symbols:
        if not symbol.start_line <= line <= symbol.end_line:
            continue
        if best is None or _span(symbol) < _span(best):
            best = symbol
    return best


def _span(symbol: Symbol) -> int:
    return symbol.end_line - symbol.start_line


def symbol_id(path: str, name: str, start_line: int) -> str:
    """Build the stable id for a definition.

    The start line is part of the identity because one file can define the same
    name twice — an overload, or a name reused across two classes — and without
    it those rows would collapse into one under ``INSERT OR REPLACE``.
    """
    return f"sym:{path}:{name}:{start_line}"


def reference_id(src_symbol: str, name: str, line: int, column: int) -> str:
    """Build the stable id for one mention.

    The column is part of the identity because one line can mention the same
    name twice — ``f(g(x), g(y))`` — and keyed on the line alone those two
    mentions would collapse into one row under ``INSERT OR REPLACE``.
    """
    digest: str = hashlib.sha256(
        f"{src_symbol}|{name}|{line}|{column}".encode()
    ).hexdigest()[:16]
    return f"ref:{digest}"
