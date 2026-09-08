"""Extract named definition captures from tree-sitter syntax trees."""

from importlib import resources

from tree_sitter import Node, Query, QueryCursor
from tree_sitter_language_pack import get_language

from smritikosh.engine import sm
from smritikosh.models import Capture, ParsedFile

_QUERY_CACHE: dict[str, Query] = {}


def _load_query(language: str) -> Query:
    """Load and cache the packaged tags query for a language."""
    cached_query: Query | None = _QUERY_CACHE.get(language)
    if cached_query is not None:
        return cached_query

    query_ref = resources.files("smritikosh.queries") / language / "tags.scm"
    query_source: str = query_ref.read_text(encoding="utf-8")
    query: Query = Query(get_language(language), query_source)
    _QUERY_CACHE[language] = query
    return query


@sm.tracked
def _extract(parsed: ParsedFile, has_tags_scm: bool) -> list[Capture]:
    """Extract named definitions using the parsed file's packaged tags query."""
    if not has_tags_scm:
        return []

    query: Query = _load_query(parsed.language)
    matches = QueryCursor(query).matches(parsed.tree.root_node)
    result: list[Capture] = []
    for _, capture_dict in matches:
        name_nodes: list[Node] = capture_dict.get("name", [])
        if not name_nodes:
            continue
        name: str = name_nodes[0].text.decode("utf-8")
        for capture_name, nodes in capture_dict.items():
            if not capture_name.startswith("definition."):
                continue
            for node in nodes:
                result.append(
                    Capture(
                        capture_name=capture_name,
                        node=node,
                        name=name,
                        path=parsed.path,
                    )
                )
    return result
