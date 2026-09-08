"""Select the files worth indexing -- three gates over a FileSource."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import Final

from smritikosh.indexing.file_router import FileRouter
from smritikosh.models import SourceFile
from smritikosh.ports.file_source import FileSource

__all__ = ["DEFAULT_EXCLUDE_DIRS", "iter_source_files"]

DEFAULT_EXCLUDE_DIRS: Final = frozenset(
    {
        ".cache",
        ".git",
        ".mypy_cache",
        ".next",
        ".pytest_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "htmlcov",
        "node_modules",
        "target",
        "venv",
    }
)


def iter_source_files(source: FileSource, router: FileRouter) -> Iterator[SourceFile]:
    """Yield one SourceFile per path that clears all three gates.

    Routing happens here, once per file, and rides on the SourceFile so that no
    later stage re-derives it from the path.
    """
    for path in source.iter_paths():
        if _in_excluded_dir(path):
            continue  # Gate 1
        if source.is_ignored(path):
            continue  # Gate 2
        route = router.route(path)
        if route is None:
            continue  # Gate 3

        yield SourceFile(
            path=path,
            language=route.language,
            content=source.read_text(path),
            has_tags_scm=route.has_tags_scm,
            strategy=route.strategy,
        )


def _in_excluded_dir(path: str) -> bool:
    """Return True when any directory segment of path is build or tool noise."""
    segments = PurePosixPath(path).parts[:-1]
    return any(segment in DEFAULT_EXCLUDE_DIRS for segment in segments)
