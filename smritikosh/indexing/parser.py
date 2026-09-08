"""Stage 1: tree-sitter parse -- source files -> AST per file.

File selection lives in indexing/discovery.py; this module only parses.
"""

from smritikosh.models import ParsedFile, SourceFile


def parse_file(source: SourceFile) -> ParsedFile:
    """Parse a single source file into an AST using tree-sitter.

    TODO: load the right tree-sitter grammar for source.language.
    """
    raise NotImplementedError
