"""Integration tests for FastEmbedEmbedder — runs against the real ONNX model."""

import pytest

from smritikosh.adapters.embedder.fastembed import FastEmbedEmbedder

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def embedder() -> FastEmbedEmbedder:
    return FastEmbedEmbedder()


def test_should_embed_a_document_to_a_vector_of_model_width(
    embedder: FastEmbedEmbedder,
) -> None:
    vectors = embedder.encode_documents(["def load_orders(path): ..."])

    assert len(vectors[0]) == embedder.dims


def test_dims_matches_actual_vector_length(embedder: FastEmbedEmbedder) -> None:
    """dims property must agree with the real output shape — no dummy needed."""
    vectors = embedder.encode_documents(["x = 1"])

    assert embedder.dims == len(vectors[0])


def test_model_id_contains_model_name_and_dims(embedder: FastEmbedEmbedder) -> None:
    assert embedder._model_name in embedder.model_id
    assert str(embedder.dims) in embedder.model_id


def test_encode_documents_returns_list_of_float_lists(
    embedder: FastEmbedEmbedder,
) -> None:
    result = embedder.encode_documents(["foo()", "bar()"])

    assert len(result) == 2
    assert all(isinstance(v, list) for v in result)
    assert all(isinstance(x, float) for x in result[0])


def test_encode_queries_returns_same_shape_as_documents(
    embedder: FastEmbedEmbedder,
) -> None:
    docs = embedder.encode_documents(["def foo(): pass"])
    queries = embedder.encode_queries(["find function foo"])

    assert len(docs[0]) == len(queries[0])
