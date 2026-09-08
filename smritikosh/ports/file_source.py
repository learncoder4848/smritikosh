"""The file-source contract -- implementations live in adapters/file_source/."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

__all__ = ["FileSource"]


class FileSource(ABC):
    """Supplies indexable paths and their contents from one backing store."""

    @abstractmethod
    def iter_paths(self) -> Iterator[str]:
        """Yield source-relative posix keys in a deterministic order."""

    @abstractmethod
    def read_text(self, path: str) -> str:
        """Return the contents of path, replacing undecodable bytes."""

    def is_ignored(self, path: str) -> bool:
        """Return True when the store's own ignore rules exclude path.

        Concrete rather than abstract: a store with no ignore convention, such
        as a blob bucket, inherits this and skips the gate entirely.
        """
        return False
