"""The whole loop: embed real snippets, store them, and retrieve by meaning."""

import hashlib
from pathlib import Path

import pytest

from smritikosh.adapters.embedder.sentence_transformer import (
    SentenceTransformerEmbedder,
)
from smritikosh.adapters.vector_store.duckdb import DuckDBVectorStore

pytestmark = pytest.mark.slow

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

SNIPPETS = (CSV_SNIPPET, RETRY_SNIPPET)


def chunk_id_for(text: str) -> str:
    """Mirror the content-hash chunk ID the indexing pipeline will use."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# Module-scoped: loading the model costs seconds and ~3GB, so do it once.
@pytest.fixture(scope="module")
def embedder() -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder()


@pytest.fixture(scope="module")
def store(
    tmp_path_factory: pytest.TempPathFactory,
    embedder: SentenceTransformerEmbedder,
) -> DuckDBVectorStore:
    db_path: Path = tmp_path_factory.mktemp("index") / "smritikosh.duckdb"
    store = DuckDBVectorStore(str(db_path))
    store.setup(embedder.dims)

    vectors = embedder.encode_documents(list(SNIPPETS))
    for text, vector in zip(SNIPPETS, vectors, strict=True):
        store.upsert(chunk_id_for(text), vector)

    return store


def test_should_retrieve_the_csv_snippet_when_asked_about_csv_files(
    store: DuckDBVectorStore,
    embedder: SentenceTransformerEmbedder,
) -> None:
    query = embedder.encode_queries(["how do I read rows out of a CSV file"])[0]

    hits = store.search(query, top_k=2)

    assert hits[0][0] == chunk_id_for(CSV_SNIPPET)


def test_should_not_duplicate_rows_when_a_chunk_is_reindexed(
    store: DuckDBVectorStore,
    embedder: SentenceTransformerEmbedder,
) -> None:
    query = embedder.encode_queries(["anything at all"])[0]
    store.upsert(chunk_id_for(CSV_SNIPPET), embedder.encode_documents([CSV_SNIPPET])[0])

    hits = store.search(query, top_k=10)

    assert len(hits) == len(SNIPPETS)
