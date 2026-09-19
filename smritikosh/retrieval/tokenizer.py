"""Language-neutral tokenization for lexical code retrieval."""

from __future__ import annotations

import re
from typing import Final

__all__ = ["tokenize_code"]

_RAW_TOKEN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_]+")
_CAMEL_PART: Final[re.Pattern[str]] = re.compile(
    r"[A-Z]+(?=[A-Z][a-z]|\d|\b)|[A-Z]?[a-z]+|\d+"
)


def tokenize_code(text: str) -> list[str]:
    """Tokenize prose, paths, snake_case, and camelCase identifiers."""
    tokens: list[str] = []
    for raw in _RAW_TOKEN.findall(text):
        exact: str = raw.lower()
        tokens.append(exact)
        parts: list[str] = []
        for snake_part in raw.split("_"):
            parts.extend(part.lower() for part in _CAMEL_PART.findall(snake_part))
        if parts != [exact]:
            tokens.extend(parts)
    return tokens
