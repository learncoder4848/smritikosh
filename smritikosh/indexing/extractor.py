"""Stage 2: symbol + call-graph extraction -- definitions, identifiers, call edges."""

from smritikosh.models import CallEdge, ParsedFile, Symbol


def extract_symbols(parsed: ParsedFile) -> list[Symbol]:
    """Walk the AST and extract symbol definitions (functions, classes, etc).

    TODO: implement per-language extraction logic.
    """
    raise NotImplementedError


def extract_call_edges(parsed: ParsedFile, symbols: list[Symbol]) -> list[CallEdge]:
    """Walk the AST and extract caller -> callee edges.

    TODO: resolve call expressions to known symbols.
    """
    raise NotImplementedError
