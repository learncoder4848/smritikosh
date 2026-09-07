"""Stage 2: symbol extraction from the AST."""

from smritikosh.models import ParsedFile, Symbol


def extract_symbols(parsed: ParsedFile) -> list[Symbol]:
    """Walk the AST and extract symbol definitions (functions, classes, etc).

    TODO: implement per-language extraction logic.
    """
    raise NotImplementedError
