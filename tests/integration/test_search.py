"""End-to-end search against the real embedding model and a real DuckDB file."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest

from smritikosh.embedder import SentenceTransformerEmbedder
from smritikosh.vector_store import DuckDBVectorStore

CSV_SNIPPET = '''
def load_orders(path: str) -> list[dict]:
    """Read a CSV file and return its rows."""
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))
'''

RETRY_SNIPPET = '''
def fetch_with_retry(url: str, attempts: int = 3) -> Response:
    """Issue an HTTP GET, retrying with exponential backoff."""
    for attempt in range(attempts):
        try:
            return httpx.get(url)
        except httpx.TransportError:
            time.sleep(2**attempt)
    raise RuntimeError("all attempts failed")
'''

SORT_SNIPPET = '''
def quicksort(values: list[int]) -> list[int]:
    """Sort a list of integers using quicksort."""
    if len(values) <= 1:
        return values
    pivot, *rest = values
    smaller = [value for value in rest if value < pivot]
    larger = [value for value in rest if value >= pivot]
    return quicksort(smaller) + [pivot] + quicksort(larger)
'''

SNIPPETS = (CSV_SNIPPET, RETRY_SNIPPET, SORT_SNIPPET)


def chunk_id_for(text: str) -> str:
    """Mirror the content-hash chunk ID the indexing pipeline will use."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


@dataclass
class Corpus:
    """An indexed corpus plus the id-to-text map that S6 will eventually own."""

    store: DuckDBVectorStore
    embedder: SentenceTransformerEmbedder
    texts: dict[str, str]

    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        query_vector = self.embedder.encode_queries([query])[0]
        return self.store.search(query_vector, top_k)


# Module-scoped: loading the model costs seconds and ~1GB, so do it once.
@pytest.fixture(scope="module")
def corpus(tmp_path_factory: pytest.TempPathFactory) -> Corpus:
    db_path: Path = tmp_path_factory.mktemp("index") / "smritikosh.duckdb"
    embedder = SentenceTransformerEmbedder()
    store = DuckDBVectorStore(str(db_path))
    store.setup(embedder.dims)

    vectors = embedder.encode_documents(list(SNIPPETS))
    for text, vector in zip(SNIPPETS, vectors, strict=True):
        store.upsert(chunk_id_for(text), vector)

    return Corpus(
        store=store,
        embedder=embedder,
        texts={chunk_id_for(text): text for text in SNIPPETS},
    )


def test_should_rank_the_csv_snippet_first_when_asked_about_csv_files(
    corpus: Corpus,
) -> None:
    # Act
    hits = corpus.search("how do I read rows out of a CSV file")

    # Assert
    assert corpus.texts[hits[0][0]] == CSV_SNIPPET


def test_should_rank_the_retry_snippet_first_when_asked_about_http_retries(
    corpus: Corpus,
) -> None:
    # Act
    hits = corpus.search("retry a failed network request with backoff")

    # Assert
    assert corpus.texts[hits[0][0]] == RETRY_SNIPPET


def test_should_return_scores_in_descending_order_when_searching(
    corpus: Corpus,
) -> None:
    # Act
    hits = corpus.search("how do I read rows out of a CSV file")

    # Assert
    assert [score for _, score in hits] == sorted(
        (score for _, score in hits), reverse=True
    )


def test_should_limit_results_when_top_k_is_smaller_than_the_corpus(
    corpus: Corpus,
) -> None:
    # Act
    hits = corpus.search("how do I read rows out of a CSV file", top_k=2)

    # Assert
    assert len(hits) == 2


def test_should_not_duplicate_rows_when_the_same_chunk_is_reindexed(
    corpus: Corpus,
) -> None:
    # Arrange
    vector = corpus.embedder.encode_documents([CSV_SNIPPET])[0]

    # Act
    corpus.store.upsert(chunk_id_for(CSV_SNIPPET), vector)

    # Assert
    assert len(corpus.search("anything at all", top_k=10)) == len(SNIPPETS)
