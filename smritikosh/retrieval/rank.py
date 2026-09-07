"""Fusion, dedup, and reranking helpers used by HybridRetriever."""

from smritikosh.models import SearchResult


def reciprocal_rank_fusion(
    result_lists: list[list[SearchResult]], k: int = 60
) -> list[SearchResult]:
    """Combine multiple ranked result lists into one fused ranking.

    TODO: implement RRF (or weighted score fusion) across result_lists.
    """
    raise NotImplementedError


def dedup(results: list[SearchResult]) -> list[SearchResult]:
    """Remove duplicate/overlapping results (same path + overlapping line ranges).

    TODO: implement overlap-aware dedup.
    """
    raise NotImplementedError


def rerank(query: str, results: list[SearchResult]) -> list[SearchResult]:
    """Optionally rerank fused results (e.g. cross-encoder, heuristic boosts).

    TODO: implement reranking, or pass through if not needed.
    """
    raise NotImplementedError
