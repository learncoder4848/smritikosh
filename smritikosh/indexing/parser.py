"""Stage 1: tree-sitter parse -- source files -> AST per file."""

from collections.abc import Iterator

from smritikosh.models import ParsedFile, SourceFile


def iter_source_files(repo_path: str) -> Iterator[SourceFile]:
    """Walk the repository and yield source files to parse.

    TODO: respect .gitignore, filter by supported extensions/languages.
    """
    raise NotImplementedError


def parse_file(source: SourceFile) -> ParsedFile:
    """Parse a single source file into an AST using tree-sitter.

    TODO: load the right tree-sitter grammar for source.language.
    """
    raise NotImplementedError
