"""Local filesystem source -- walks a repo directory and honours .gitignore."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Final

import pathspec

from smritikosh.ports.file_source import FileSource

__all__ = ["LocalFileSource"]

GITIGNORE_NAME: Final = ".gitignore"


class LocalFileSource(FileSource):
    """Reads files from a directory tree on disk."""

    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._spec = _load_gitignore(self._root)

    def iter_paths(self) -> Iterator[str]:
        # sorted() so two runs over an unchanged tree yield the same order,
        # which the file-level memoization relies on.
        for path in sorted(self._root.rglob("*")):
            if path.is_file():
                yield path.relative_to(self._root).as_posix()

    def read_text(self, path: str) -> str:
        return (self._root / path).read_text(errors="replace")

    def is_ignored(self, path: str) -> bool:
        return self._spec is not None and self._spec.match_file(path)


def _load_gitignore(root: Path) -> pathspec.PathSpec | None:
    """Compile the repo-root .gitignore, or return None when there is none."""
    gitignore = root / GITIGNORE_NAME
    if not gitignore.is_file():
        return None
    return pathspec.PathSpec.from_lines(
        "gitignore", gitignore.read_text(errors="replace").splitlines()
    )
