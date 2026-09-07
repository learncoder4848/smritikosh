"""Tests for the sentence-transformers embedder, against the real model."""

import pytest

from smritikosh.adapters.embedder.sentence_transformer import (
    SentenceTransformerEmbedder,
)

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def embedder() -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder()


def test_should_embed_a_document_to_a_vector_of_model_width(
    embedder: SentenceTransformerEmbedder,
) -> None:
    vectors = embedder.encode_documents(["def load_orders(path): ..."])

    assert len(vectors[0]) == embedder.dims


def test_should_embed_the_same_text_differently_as_query_and_document(
    embedder: SentenceTransformerEmbedder,
) -> None:
    # Identical vectors would mean the nl2code task prefixes are not being applied,
    # which degrades retrieval silently rather than failing.
    text = "read rows from a csv file"

    assert embedder.encode_documents([text]) != embedder.encode_queries([text])
