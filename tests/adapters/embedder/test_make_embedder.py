"""Tests for smritikosh.adapters.embedder.make_embedder factory.

These tests exercise the *adapter layer* in isolation — no Click, no CLI.
The CLI wrapper (_make_embedder in cli.py) is tested separately in test_cli.py,
where the conversion of ValueError → BadParameter is checked.
"""

from __future__ import annotations

import pytest

from smritikosh.adapters.embedder import EMBEDDER_CHOICES, make_embedder

# ── EMBEDDER_CHOICES ──────────────────────────────────────────────────────────


def test_embedder_choices_contains_all_supported_backends() -> None:
    assert set(EMBEDDER_CHOICES) == {"jina"}


def test_embedder_choices_is_a_list_of_strings() -> None:
    assert isinstance(EMBEDDER_CHOICES, list)
    assert all(isinstance(c, str) for c in EMBEDDER_CHOICES)


# ── make_embedder — jina ──────────────────────────────────────────────────────


def test_make_embedder_jina_returns_sentence_transformer_embedder() -> None:
    from smritikosh.adapters.embedder.sentence_transformer import (
        SentenceTransformerEmbedder,
    )

    assert isinstance(make_embedder("jina"), SentenceTransformerEmbedder)


def test_make_embedder_jina_is_case_insensitive() -> None:
    from smritikosh.adapters.embedder.sentence_transformer import (
        SentenceTransformerEmbedder,
    )

    for variant in ("Jina", "JINA", "jInA"):
        assert isinstance(make_embedder(variant), SentenceTransformerEmbedder), variant


# ── make_embedder — unknown name ──────────────────────────────────────────────


def test_make_embedder_unknown_name_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown embedder"):
        make_embedder("bert")


def test_make_embedder_value_error_mentions_valid_choices() -> None:
    with pytest.raises(ValueError) as exc_info:
        make_embedder("gpt")
    message = str(exc_info.value)
    for choice in EMBEDDER_CHOICES:
        assert choice in message
