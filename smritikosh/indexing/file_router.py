"""Route a file path to its language and chunking strategy."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import PurePosixPath
from typing import Final

from smritikosh.models import ChunkingStrategy

__all__ = ["FileRouter", "JsonExcludeFilter", "RouteConfig"]

JSON_SUFFIX: Final = ".json"


@dataclass(frozen=True)
class RouteConfig:
    """How one selected file is handled downstream."""

    language: str
    strategy: ChunkingStrategy
    has_tags_scm: bool


class JsonExcludeFilter:
    """Excludelist for .json paths -- anything not listed here is indexed."""

    DEFAULT_EXCLUDE_FILENAMES: Final = frozenset(
        {
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "composer.lock",
            "Pipfile.lock",
        }
    )
    DEFAULT_EXCLUDE_FILENAME_PATTERNS: Final = (
        "*-lock.json",
        "*.min.json",
        "*.chunk.json",
    )
    DEFAULT_EXCLUDE_DIR_SEGMENTS: Final = frozenset(
        {
            "__fixtures__",
            "fixtures",
            "testdata",
            "test_data",
            "coverage",
            "htmlcov",
            ".next",
            "generated",
        }
    )

    def __init__(
        self,
        extra_filenames: Iterable[str] | None = None,
        extra_patterns: Iterable[str] | None = None,
        extra_dirs: Iterable[str] | None = None,
    ) -> None:
        self._filenames = self.DEFAULT_EXCLUDE_FILENAMES | frozenset(
            extra_filenames or ()
        )
        self._patterns = self.DEFAULT_EXCLUDE_FILENAME_PATTERNS + tuple(
            extra_patterns or ()
        )
        self._dirs = self.DEFAULT_EXCLUDE_DIR_SEGMENTS | frozenset(extra_dirs or ())

    def is_excluded(self, path: str) -> bool:
        """Return True when path is machine-generated or fixture JSON."""
        parts = PurePosixPath(path).parts
        filename = parts[-1]

        if filename in self._filenames:
            return True
        if any(fnmatch(filename, pattern) for pattern in self._patterns):
            return True
        # parts[:-1] -- directory segments only, so a file named "fixtures" stays.
        return any(segment in self._dirs for segment in parts[:-1])


class FileRouter:
    """Maps a path to its RouteConfig. A new file type is one register call."""

    def __init__(self, json_exclude_filter: JsonExcludeFilter | None = None) -> None:
        self._json_filter = json_exclude_filter or JsonExcludeFilter()
        self._by_extension: dict[str, RouteConfig] = {}
        self._by_filename: dict[str, RouteConfig] = {}

    def register_extension(
        self,
        ext: str,
        language: str,
        strategy: ChunkingStrategy,
        has_tags_scm: bool = True,
    ) -> None:
        """Route files ending in ext, matched case-insensitively."""
        self._by_extension[ext.lower()] = RouteConfig(language, strategy, has_tags_scm)

    def register_filename(
        self,
        filename: str,
        language: str,
        strategy: ChunkingStrategy,
        has_tags_scm: bool = True,
    ) -> None:
        """Route files named exactly filename, ahead of any extension rule."""
        self._by_filename[filename] = RouteConfig(language, strategy, has_tags_scm)

    def route(self, path: str) -> RouteConfig | None:
        """Return the config for path, or None when it must not be indexed."""
        pure = PurePosixPath(path)

        by_filename = self._by_filename.get(pure.name)
        if by_filename is not None:
            return by_filename

        suffix = pure.suffix.lower()
        if suffix == JSON_SUFFIX and self._json_filter.is_excluded(path):
            return None

        return self._by_extension.get(suffix)
