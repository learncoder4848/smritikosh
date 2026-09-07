"""Tests for the embedding backends."""

import asyncio
import sys
import types

import numpy as np
import pytest

from smritikosh.embedder import DEFAULT_MODEL, SentenceTransformerEmbedder


class FakeSentenceTransformer:
    """Stands in for the real model so tests never load weights."""

    def __init__(self, model_name: str, **kwargs: object) -> None:
        self.model_name = model_name
        self.kwargs = kwargs
        self.calls: list[tuple[list[str], str]] = []

    def get_sentence_embedding_dimension(self) -> int:
        return 896

    def encode(self, texts: list[str], prompt_name: str) -> np.ndarray:
        self.calls.append((list(texts), prompt_name))
        return np.array([[float(index), 0.0] for index in range(len(texts))])


@pytest.fixture
def loaded_models(monkeypatch: pytest.MonkeyPatch) -> list[FakeSentenceTransformer]:
    """Replace the module the embedder imports lazily, and record what it built."""
    loaded: list[FakeSentenceTransformer] = []

    def factory(model_name: str, **kwargs: object) -> FakeSentenceTransformer:
        model = FakeSentenceTransformer(model_name, **kwargs)
        loaded.append(model)
        return model

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        types.SimpleNamespace(SentenceTransformer=factory),
    )
    return loaded


def test_should_not_load_model_when_constructed(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Act
    SentenceTransformerEmbedder()

    # Assert
    assert loaded_models == []


def test_should_apply_document_prefix_when_encoding_documents(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Arrange
    embedder = SentenceTransformerEmbedder()

    # Act
    embedder.encode_documents(["def read_csv(): ..."])

    # Assert
    assert loaded_models[0].calls == [(["def read_csv(): ..."], "nl2code_document")]


def test_should_apply_query_prefix_when_encoding_queries(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Arrange
    embedder = SentenceTransformerEmbedder()

    # Act
    embedder.encode_queries(["how to read a csv"])

    # Assert
    assert loaded_models[0].calls == [(["how to read a csv"], "nl2code_query")]


def test_should_preserve_order_when_encoding_a_batch(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Arrange
    embedder = SentenceTransformerEmbedder()

    # Act
    vectors = embedder.encode_documents(["first", "second", "third"])

    # Assert
    assert vectors == [[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]]


def test_should_reuse_loaded_model_when_encoding_twice(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Arrange
    embedder = SentenceTransformerEmbedder()

    # Act
    embedder.encode_documents(["first"])
    embedder.encode_queries(["second"])

    # Assert
    assert len(loaded_models) == 1


def test_should_report_native_dims_when_not_truncating(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Arrange
    embedder = SentenceTransformerEmbedder()

    # Act
    dims = embedder.dims

    # Assert
    assert dims == 896


def test_should_report_truncated_dims_when_truncating(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Arrange
    embedder = SentenceTransformerEmbedder(truncate_dim=256)

    # Act
    dims = embedder.dims

    # Assert
    assert dims == 256


def test_should_track_dims_in_model_id_when_truncating(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Arrange
    embedder = SentenceTransformerEmbedder(truncate_dim=256)

    # Act
    model_id = embedder.model_id

    # Assert
    assert model_id == f"{DEFAULT_MODEL}:256"


def test_should_return_one_vector_when_embedding_a_query(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Arrange
    embedder = SentenceTransformerEmbedder()

    # Act
    vector = asyncio.run(embedder.embed_query("how to read a csv"))

    # Assert
    assert vector == [0.0, 0.0]


def test_should_use_query_prefix_when_embedding_a_query(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Arrange
    embedder = SentenceTransformerEmbedder()

    # Act
    asyncio.run(embedder.embed_query("how to read a csv"))

    # Assert
    assert loaded_models[0].calls[0][1] == "nl2code_query"


def test_should_use_document_prefix_when_embedding_a_document(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Arrange
    embedder = SentenceTransformerEmbedder()

    # Act
    asyncio.run(embedder.embed_document("def read_csv(): ..."))

    # Assert
    assert loaded_models[0].calls[0][1] == "nl2code_document"


def test_should_return_a_vector_per_text_when_embedding_a_batch(
    loaded_models: list[FakeSentenceTransformer],
) -> None:
    # Arrange
    embedder = SentenceTransformerEmbedder()

    # Act
    vectors = asyncio.run(embedder.embed_documents_batch(["first", "second"]))

    # Assert
    assert vectors == [[0.0, 0.0], [1.0, 0.0]]
