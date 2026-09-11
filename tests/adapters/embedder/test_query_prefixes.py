"""Tests for CodeRankEmbed wiring — no model load required."""

from __future__ import annotations

import pickle

from smritikosh.adapters.embedder.fastembed import (
    _CODE_INSTRUCTION,
    _MODEL_DIM,
    _MODEL_REPO,
    FastEmbedEmbedder,
)
from smritikosh.constants import DEFAULT_MODEL


def test_dims_resolve_without_loading_onnx() -> None:
    e = FastEmbedEmbedder()

    assert e.dims == _MODEL_DIM
    assert e.dims == 768
    assert e._model is None


def test_model_is_coderankembed() -> None:
    e = FastEmbedEmbedder()

    assert e._model_name == DEFAULT_MODEL
    assert e._model_name == "nomic-ai/CodeRankEmbed"
    assert _MODEL_REPO == "mrsladoje/CodeRankEmbed-onnx-int8"


def test_embedder_sets_query_instruction_at_construction_without_loading() -> None:
    """Constructing must not touch ONNX — the instruction is a constant."""
    e = FastEmbedEmbedder()

    assert e._model is None
    assert e._query_prefix == _CODE_INSTRUCTION


def test_query_instruction_survives_the_pickle_round_trip() -> None:
    """The engine pickles the embedder for cache fingerprinting."""
    e = pickle.loads(pickle.dumps(FastEmbedEmbedder()))

    assert e._query_prefix == _CODE_INSTRUCTION


def test_query_prefix_is_part_of_the_change_fingerprint() -> None:
    """Editing the instruction must not share a memo cache key."""
    e = FastEmbedEmbedder()
    other = FastEmbedEmbedder()
    other._query_prefix = "a different instruction: "

    assert pickle.dumps(e) != pickle.dumps(other)
