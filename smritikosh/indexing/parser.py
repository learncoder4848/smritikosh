"""Stage 1: tree-sitter parse -- source files -> AST per file.

File selection lives in indexing/discovery.py; this module only parses.
"""

from __future__ import annotations

from tree_sitter import Language, Parser, Tree
from tree_sitter_language_pack import get_language

from smritikosh.engine import sm
from smritikosh.models import ParsedFile, SourceFile

__all__ = ["parse_file"]

# Grammar handles only. A Language is an immutable pointer into a shared library
# the process has already loaded, so worker threads can share one; a Parser
# carries mutable state across parse() and is built per call instead.
_LANGUAGE_CACHE: dict[str, Language] = {}


def _get_language(language: str) -> Language:
    """Return the grammar handle for language, loading it on first use."""
    cached: Language | None = _LANGUAGE_CACHE.get(language)
    if cached is not None:
        return cached

    grammar: Language = get_language(language)
    _LANGUAGE_CACHE[language] = grammar
    return grammar


@sm.tracked
def parse_file(source: SourceFile) -> ParsedFile:
    """Parse one already-routed source file into a tree-sitter AST.

    CPU-bound, and called through @sm.threaded because the tree-sitter C
    extension releases the GIL. Malformed input needs no handling here: a parse
    never raises, it returns a tree holding ERROR nodes.
    """
    parser = Parser(_get_language(source.language))
    tree: Tree = parser.parse(source.content.encode("utf-8"))
    return ParsedFile(
        path=source.path,
        language=source.language,
        content=source.content,
        tree=tree,
    )
