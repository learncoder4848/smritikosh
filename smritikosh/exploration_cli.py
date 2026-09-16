"""CLI commands for read-only, agent-driven index exploration."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Final, TextIO, cast

import click
import toons

from smritikosh.adapters.embedder import make_embedder
from smritikosh.adapters.retrieval.duckdb import (
    DuckDBBm25Store,
    DuckDBDenseRetriever,
    DuckDBLexicalRetriever,
)
from smritikosh.adapters.retrieval.source import DuckDBSourceReader
from smritikosh.constants import DEFAULT_DB_PATH
from smritikosh.exploration import (
    IndexedChunk,
    OutlineEntry,
    ReadOnlyExplorer,
    SearchOptions,
    SourceLine,
    TextMatch,
)
from smritikosh.models import EvidenceOptions, EvidencePack, SearchResult
from smritikosh.ports.embedder import Embedder
from smritikosh.retrieval.service import EvidenceService

__all__ = ["explore"]

TOOL_MANIFEST: Final[dict[str, object]] = {
    "version": 5,
    "flow": (
        "For broad questions run evidence with 4-8 focused query arguments, "
        "then at most one chunks --range follow-up. Use batch for already-known "
        "mixed operations. Never request whole-file source unless essential."
    ),
    # One line per tool: the manifest is read by an agent on every session, so
    # its own size is a cost, and nested argument tables cost more than they
    # explain about a command whose usage string already names its options.
    "tools": {
        "search": (
            "explore search QUERY... [--top-k N] [--include-path LIKE] "
            "[--exclude-path LIKE] [--context N] [--full] — code by meaning; "
            "reports locations by default; loads the embedding model"
        ),
        "chunks": (
            "explore chunks [PATH] [--start-line N] [--end-line M] [--full] "
            "[--range PATH START END]... — outline one file or read one or more "
            "source ranges"
        ),
        "text": (
            "explore text TEXT [--path PATH] [--limit N] — exact symbol or "
            "string, as path:line: line"
        ),
        "paths": "explore paths PATTERN [--limit N] — paths containing a substring",
        "info": "explore info — index size and embedding dimensions",
        "batch": (
            "explore batch — NDJSON on stdin; each row uses op (or tool): "
            'search {queries:[...] or query:"...",top_k,context}, chunks '
            "{path,start_line?,end_line?}, text {text,path?,limit?}, paths "
            "{pattern,limit?}, or info; resources stay warm"
        ),
        "evidence": (
            "explore evidence QUERY... [--per-query N] [--max-results N] "
            "[--max-chars N] — bounded dense+BM25 evidence fused with RRF, "
            "selected for facet coverage and diversity, then expanded one hop"
        ),
    },
    "notes": (
        "Prefix every command with `smritikosh `. Output is TOON; --prose "
        "switches to prose. All but tools take --db-path INDEX. Source "
        "lines print as numbered text either way."
    ),
}


def _echo_toon(value: object) -> None:
    """Emit TOON — a declared schema for roughly half of JSON's tokens."""
    click.echo(toons.dumps(value))


def _echo_chunks(chunks: list[IndexedChunk]) -> None:
    if not chunks:
        click.echo("No chunks found.")
        return
    for chunk in chunks:
        kind: str = f"  [{chunk.chunk_kind}]" if chunk.chunk_kind else ""
        click.echo(f"{chunk.path}:{chunk.start_line}-{chunk.end_line}{kind}")
        for line in chunk.text.splitlines():
            click.echo(f"    {line}")
        click.echo()


def _echo_outline(entries: list[OutlineEntry], *, path: str) -> None:
    if not entries:
        click.echo("Nothing indexed for that path.")
        return
    click.echo(f"{path}  ({len(entries)} entries)")
    width: int = max(len(f"{e.start_line}-{e.end_line}") for e in entries)
    for entry in entries:
        span: str = f"{entry.start_line}-{entry.end_line}"
        kind: str = entry.chunk_kind or "chunk"
        name: str = entry.symbol or "-"
        click.echo(f"{span:<{width}}  {kind}  {name}")


def _echo_text_matches(matches: list[TextMatch]) -> None:
    if not matches:
        click.echo("No matches found.")
        return
    for match in matches:
        # "~" warns that the line sits somewhere in a chunk that cannot be
        # mapped line by line, so the number is the chunk's start, not the hit.
        marker: str = "" if match.exact_line else "~"
        click.echo(f"{match.path}:{marker}{match.line_number}: {match.text}")


def _echo_source_lines(lines: list[SourceLine], *, path: str) -> None:
    if not lines:
        click.echo("No source lines found.")
        return
    click.echo(f"{path}:{lines[0].line_number}-{lines[-1].line_number}")
    width: int = len(str(lines[-1].line_number))
    for line in lines:
        click.echo(f"{line.line_number:>{width}}  {line.text}")


def _numbered_source(lines: list[SourceLine]) -> str:
    """Format source lines compactly while preserving their exact locations."""
    if not lines:
        return ""
    width: int = len(str(lines[-1].line_number))
    return "\n".join(f"{line.line_number:>{width}}  {line.text}" for line in lines)


def _result_payload(
    result: SearchResult,
    *,
    full: bool,
    context: str | None = None,
) -> dict[str, object]:
    """Serialize one hit, carrying its code only when it was asked for."""
    payload: dict[str, object] = asdict(result)
    # Cosine scores separate hits in the third decimal at most; the float's
    # remaining sixteen digits are tokens spent on noise.
    payload["score"] = round(result.score, 3)
    if not full:
        del payload["snippet"]
    if context is not None:
        payload["context"] = context
    return payload


def _source_context(
    explorer: ReadOnlyExplorer,
    result: SearchResult,
    *,
    context_lines: int,
) -> str:
    """Read numbered source spanning a search hit and its surrounding lines."""
    lines: list[SourceLine] = explorer.get_source_lines(
        result.path,
        start_line=max(1, result.start_line - context_lines),
        end_line=result.end_line + context_lines,
    )
    return _numbered_source(lines)


def _search_payloads(
    explorer: ReadOnlyExplorer,
    results: list[SearchResult],
    *,
    full: bool,
    context_lines: int | None,
) -> list[dict[str, object]]:
    """Serialize search results and optionally attach numbered source context."""
    return [
        _result_payload(
            result,
            full=full,
            context=(
                _source_context(explorer, result, context_lines=context_lines)
                if context_lines is not None
                else None
            ),
        )
        for result in results
    ]


def _echo_location(result: SearchResult) -> None:
    kind: str = f"  {result.chunk_kind}" if result.chunk_kind else ""
    symbol: str = f"  {result.symbol}" if result.symbol else ""
    click.echo(
        f"{result.path}:{result.start_line}-{result.end_line}  "
        f"{result.score:.3f}{kind}{symbol}"
    )


def _echo_results(
    results: list[SearchResult],
    *,
    elapsed_ms: float,
    full: bool,
    contexts: list[str] | None = None,
) -> None:
    if not results:
        click.echo(f"No results found.  ({elapsed_ms:.0f} ms)")
        return
    click.echo(f"Found {len(results)} result(s) in {elapsed_ms:.0f} ms:\n")
    for index, result in enumerate(results):
        _echo_location(result)
        # Code is what `chunks --start-line` is for. Shipping it with every
        # hit was three quarters of a search result, and a caller that means
        # to read one of them pays for the other four.
        if full:
            for line in result.snippet.splitlines():
                click.echo(f"    {line}")
            click.echo()
        elif contexts is not None:
            click.echo(contexts[index])
            click.echo()


@click.group()
def explore() -> None:
    """Explore an existing index through read-only agent-friendly commands."""


@explore.command("tools")
@click.option(
    "--prose",
    is_flag=True,
    help="Print prose for a human instead of the default TOON rows.",
)
@click.option(
    # Accepted and ignored: TOON is the default now, but these names are
    # written into agent prompts that predate it, and failing those with
    # "no such option" costs a whole turn to rediscover an unchanged command.
    "--toon",
    "--json-output",
    "--json_output",
    is_flag=True,
    hidden=True,
)
@click.option(
    "--db-path",
    "--db_path",
    type=click.Path(),
    hidden=True,
)
def list_tools(
    prose: bool,
    toon: bool,  # noqa: ARG001
    db_path: str | None,  # noqa: ARG001
) -> None:
    """Describe exploration commands and the recommended agent workflow."""
    if not prose:
        _echo_toon(TOOL_MANIFEST)
        return
    click.echo(f"{TOOL_MANIFEST['flow']}\n")
    tools: dict[str, str] = cast(dict[str, str], TOOL_MANIFEST["tools"])
    for name, usage in tools.items():
        click.echo(f"{name}: smritikosh {usage}")
    click.echo(f"\n{TOOL_MANIFEST['notes']}")


@explore.command("info")
@click.option(
    "--db-path",
    "--db_path",
    default=DEFAULT_DB_PATH,
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--prose",
    is_flag=True,
    help="Print prose for a human instead of the default TOON rows.",
)
@click.option(
    # Accepted and ignored: TOON is the default now, but these names are
    # written into agent prompts that predate it, and failing those with
    # "no such option" costs a whole turn to rediscover an unchanged command.
    "--toon",
    "--json-output",
    "--json_output",
    is_flag=True,
    hidden=True,
)
def index_info(db_path: str, prose: bool, toon: bool) -> None:  # noqa: ARG001
    """Show indexed file, chunk, vector, and dimension counts."""
    with ReadOnlyExplorer(db_path) as explorer:
        info = explorer.index_info()
    if not prose:
        _echo_toon(asdict(info))
        return
    click.echo(
        f"files={info.files} chunks={info.chunks} "
        f"vectors={info.vectors} dimensions={info.dimensions}"
    )


@explore.command("search")
@click.argument("queries", nargs=-1, required=True)
@click.option(
    "--top-k",
    "--top_k",
    default=10,
    show_default=True,
    type=click.IntRange(min=1),
)
@click.option(
    "--include-path",
    "--include_path",
    multiple=True,
    help="SQL LIKE path pattern to include; repeat for multiple constraints.",
)
@click.option(
    "--exclude-path",
    "--exclude_path",
    multiple=True,
    help="SQL LIKE path pattern to exclude; repeat for multiple constraints.",
)
@click.option(
    "--full",
    is_flag=True,
    help="Include the matching code with every result.",
)
@click.option(
    "--context",
    "context_lines",
    type=click.IntRange(min=0),
    help="Include each matching chunk plus N surrounding numbered source lines.",
)
@click.option(
    "--db-path",
    "--db_path",
    default=DEFAULT_DB_PATH,
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--prose",
    is_flag=True,
    help="Print prose for a human instead of the default TOON rows.",
)
@click.option(
    # Accepted and ignored: TOON is the default now, but these names are
    # written into agent prompts that predate it, and failing those with
    # "no such option" costs a whole turn to rediscover an unchanged command.
    "--toon",
    "--json-output",
    "--json_output",
    is_flag=True,
    hidden=True,
)
def semantic_search(
    queries: tuple[str, ...],
    top_k: int,
    include_path: tuple[str, ...],
    exclude_path: tuple[str, ...],
    full: bool,
    context_lines: int | None,
    db_path: str,
    prose: bool,
    toon: bool,  # noqa: ARG001
) -> None:
    """Search semantically; pass multiple QUERY values to merge their rankings."""
    options = SearchOptions(
        top_k=top_k,
        include_paths=include_path,
        exclude_paths=exclude_path,
    )
    started_at: float = time.perf_counter()
    with ReadOnlyExplorer(db_path) as explorer:
        results = explorer.semantic_search(
            list(queries),
            embedder=make_embedder(),
            options=options,
        )
        payloads: list[dict[str, object]] = _search_payloads(
            explorer,
            results,
            full=full,
            context_lines=context_lines,
        )
    elapsed_ms: float = (time.perf_counter() - started_at) * 1000
    if not prose:
        _echo_toon(payloads)
        return
    contexts: list[str] | None = (
        [str(payload["context"]) for payload in payloads]
        if context_lines is not None
        else None
    )
    _echo_results(
        results,
        elapsed_ms=elapsed_ms,
        full=full,
        contexts=contexts,
    )


def _evidence_pack_payload(pack: EvidencePack, *, max_chars: int) -> dict[str, object]:
    """Render application evidence as a TOON-ready payload."""
    return {
        "version": 2,
        "budget_chars": max_chars,
        "covered_facets": list(pack.covered_facets),
        "missing_facets": list(pack.missing_facets),
        "truncated": pack.truncated,
        "evidence": [
            {
                "id": item.evidence_id,
                "facets": list(item.facets),
                "path": item.result.path,
                "start_line": item.result.start_line,
                "end_line": item.result.end_line,
                "chunk_kind": item.result.chunk_kind,
                "symbol": item.result.symbol,
                "source": item.source,
                "source_truncated": item.source_truncated,
                "follow_up": (
                    f"smritikosh explore chunks --range {item.result.path} "
                    f"{item.result.start_line} {item.result.end_line}"
                ),
            }
            for item in pack.items
        ],
    }


def _bounded_toon_payload(
    payload: dict[str, object],
    *,
    facets: tuple[str, ...],
    max_chars: int,
) -> str:
    """Trim complete evidence items until serialized TOON fits the hard limit."""
    evidence: list[dict[str, object]] = cast(
        list[dict[str, object]],
        payload["evidence"],
    )
    encoded: str = toons.dumps(payload)
    while len(encoded) + 1 > max_chars and evidence:
        evidence.pop()
        payload["truncated"] = True
        covered: set[str] = {
            str(facet)
            for item in evidence
            for facet in cast(list[object], item["facets"])
        }
        payload["covered_facets"] = [facet for facet in facets if facet in covered]
        payload["missing_facets"] = [facet for facet in facets if facet not in covered]
        encoded = toons.dumps(payload)
    return encoded


@explore.command("evidence")
@click.argument("queries", nargs=-1, required=True)
@click.option(
    "--per-query",
    default=3,
    show_default=True,
    type=click.IntRange(min=1, max=5, clamp=True),
)
@click.option(
    "--max-results",
    default=24,
    show_default=True,
    type=click.IntRange(min=1, max=24, clamp=True),
)
@click.option(
    "--max-source-lines",
    default=120,
    show_default=True,
    type=click.IntRange(min=1, max=120, clamp=True),
)
@click.option(
    "--max-chars",
    default=45_000,
    show_default=True,
    type=click.IntRange(min=1_000, max=45_000, clamp=True),
)
@click.option(
    "--db-path",
    "--db_path",
    default=DEFAULT_DB_PATH,
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
def collect_evidence(
    queries: tuple[str, ...],
    per_query: int,
    max_results: int,
    max_source_lines: int,
    max_chars: int,
    db_path: str,
) -> None:
    """Return bounded hybrid evidence across several focused queries."""
    queries = tuple(query[:500] for query in queries[:8])
    embedder: Embedder = make_embedder()
    reader = DuckDBSourceReader(db_path)
    lexical_store = DuckDBBm25Store(db_path, read_only=True)
    try:
        service = EvidenceService(
            (
                DuckDBDenseRetriever(reader, embedder),
                DuckDBLexicalRetriever(lexical_store, reader),
            ),
            reader,
        )
        try:
            pack: EvidencePack = service.retrieve(
                queries,
                options=EvidenceOptions(
                    candidates_per_channel=max(30, per_query * 6),
                    max_results=max_results,
                    max_source_lines=max_source_lines,
                    max_chars=max_chars,
                ),
            )
        except RuntimeError as exc:
            raise click.ClickException(str(exc)) from exc
        payload: dict[str, object] = _evidence_pack_payload(
            pack,
            max_chars=max_chars,
        )
    finally:
        lexical_store.close()
        reader.close()
    click.echo(
        _bounded_toon_payload(
            payload,
            facets=queries,
            max_chars=max_chars,
        )
    )


def _parse_batch_requests(stream: TextIO) -> list[dict[str, object]]:
    """Parse one JSON object per non-empty input line."""
    requests: list[dict[str, object]] = []
    for line_number, line in enumerate(stream, start=1):
        if not line.strip():
            continue
        try:
            value: object = json.loads(line)
        except json.JSONDecodeError as exc:
            raise click.ClickException(
                f"Invalid JSON on batch line {line_number}: {exc.msg}"
            ) from exc
        if not isinstance(value, dict):
            raise click.ClickException(
                f"Batch line {line_number} must be a JSON object"
            )
        requests.append(cast(dict[str, object], value))
    if not requests:
        raise click.ClickException("Batch input contains no requests")
    return requests


def _batch_int(
    request: dict[str, object],
    name: str,
    *,
    default: int | None = None,
    minimum: int = 0,
) -> int | None:
    """Read an optional bounded integer from a batch request."""
    value: object = request.get(name, default)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise click.ClickException(
            f"Batch field {name!r} must be an integer of at least {minimum}"
        )
    return value


def _batch_string(request: dict[str, object], name: str) -> str:
    """Read a required non-empty string from a batch request."""
    value: object = request.get(name)
    if not isinstance(value, str) or not value:
        raise click.ClickException(f"Batch field {name!r} must be a non-empty string")
    return value


def _batch_strings(request: dict[str, object], name: str) -> list[str]:
    """Read a required non-empty string list from a batch request."""
    value: object = request.get(name)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise click.ClickException(
            f"Batch field {name!r} must be a non-empty string array"
        )
    return cast(list[str], value)


def _batch_queries(request: dict[str, object]) -> list[str]:
    """Read plural queries while accepting the common singular spelling."""
    if "queries" in request:
        return _batch_strings(request, "queries")
    return [_batch_string(request, "query")]


def _batch_operation(request: dict[str, object]) -> str:
    """Read an operation name while accepting the common tool alias."""
    operation: object = request.get("op", request.get("tool"))
    if not isinstance(operation, str):
        raise click.ClickException("Batch request requires string field 'op'")
    return operation


def _run_batch_search(
    explorer: ReadOnlyExplorer,
    request: dict[str, object],
    *,
    embedder: Embedder,
) -> dict[str, object]:
    """Execute one semantic-search batch request."""
    top_k: int | None = _batch_int(request, "top_k", default=10, minimum=1)
    context_lines: int | None = _batch_int(request, "context")
    results: list[SearchResult] = explorer.semantic_search(
        _batch_queries(request),
        embedder=embedder,
        options=SearchOptions(top_k=cast(int, top_k)),
    )
    payloads: list[dict[str, object]] = _search_payloads(
        explorer,
        results,
        full=request.get("full") is True,
        context_lines=context_lines,
    )
    return {"op": "search", "results": payloads}


def _run_batch_chunks(
    explorer: ReadOnlyExplorer,
    request: dict[str, object],
) -> dict[str, object]:
    """Execute one outline or explicitly ranged source request."""
    path: str = _batch_string(request, "path")
    start_line: int | None = _batch_int(request, "start_line", minimum=1)
    end_line: int | None = _batch_int(request, "end_line", minimum=1)
    if start_line is None and end_line is None:
        entries: list[OutlineEntry] = explorer.get_outline(path)
        return {"op": "chunks", "outline": [asdict(entry) for entry in entries]}
    lines: list[SourceLine] = explorer.get_source_lines(
        path,
        start_line=start_line,
        end_line=end_line,
    )
    return {"op": "chunks", "lines": [asdict(line) for line in lines]}


def _run_batch_text(
    explorer: ReadOnlyExplorer,
    request: dict[str, object],
) -> dict[str, object]:
    """Execute one exact-text batch request."""
    limit: int | None = _batch_int(request, "limit", default=20, minimum=1)
    path_value: object = request.get("path")
    if path_value is not None and not isinstance(path_value, str):
        raise click.ClickException("Batch field 'path' must be a string")
    matches: list[TextMatch] = explorer.find_text_lines(
        _batch_string(request, "text"),
        path=cast(str | None, path_value),
        limit=cast(int, limit),
    )
    return {"op": "text", "matches": [asdict(match) for match in matches]}


def _run_batch_paths(
    explorer: ReadOnlyExplorer,
    request: dict[str, object],
) -> dict[str, object]:
    """Execute one indexed-path batch request."""
    limit: int | None = _batch_int(request, "limit", default=50, minimum=1)
    paths: list[str] = explorer.find_paths(
        _batch_string(request, "pattern"),
        limit=cast(int, limit),
    )
    return {"op": "paths", "paths": paths}


@explore.command("batch")
@click.argument("requests_file", type=click.File("r"), default="-")
@click.option(
    "--db-path",
    "--db_path",
    default=DEFAULT_DB_PATH,
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
def batch_requests(requests_file: TextIO, db_path: str) -> None:
    """Execute NDJSON search and chunks requests with warm shared resources."""
    requests: list[dict[str, object]] = _parse_batch_requests(requests_file)
    responses: list[dict[str, object]] = []
    embedder: Embedder | None = None
    with ReadOnlyExplorer(db_path) as explorer:
        for request in requests:
            operation: str = _batch_operation(request)
            if operation == "search":
                if embedder is None:
                    embedder = make_embedder()
                responses.append(
                    _run_batch_search(explorer, request, embedder=embedder)
                )
            elif operation == "chunks":
                responses.append(_run_batch_chunks(explorer, request))
            elif operation == "text":
                responses.append(_run_batch_text(explorer, request))
            elif operation == "paths":
                responses.append(_run_batch_paths(explorer, request))
            elif operation == "info":
                responses.append({"op": "info", "info": asdict(explorer.index_info())})
            else:
                raise click.ClickException(
                    f"Unsupported batch operation {operation!r}; "
                    "expected search, chunks, text, paths, or info"
                )
    _echo_toon(responses)


@explore.command("paths")
@click.argument("pattern")
@click.option("--limit", default=50, show_default=True, type=click.IntRange(min=1))
@click.option(
    "--db-path",
    "--db_path",
    default=DEFAULT_DB_PATH,
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--prose",
    is_flag=True,
    help="Print prose for a human instead of the default TOON rows.",
)
@click.option(
    # Accepted and ignored: TOON is the default now, but these names are
    # written into agent prompts that predate it, and failing those with
    # "no such option" costs a whole turn to rediscover an unchanged command.
    "--toon",
    "--json-output",
    "--json_output",
    is_flag=True,
    hidden=True,
)
def find_paths(
    pattern: str,
    limit: int,
    db_path: str,
    prose: bool,
    toon: bool,  # noqa: ARG001
) -> None:
    """Find indexed paths containing PATTERN."""
    with ReadOnlyExplorer(db_path) as explorer:
        paths: list[str] = explorer.find_paths(pattern, limit=limit)
    if not prose:
        _echo_toon(paths)
        return
    click.echo("\n".join(paths) if paths else "No paths found.")


@explore.command("text")
@click.argument("text")
@click.option("--path", help="Restrict results to one exact indexed path.")
@click.option("--limit", default=20, show_default=True, type=click.IntRange(min=1))
@click.option(
    "--db-path",
    "--db_path",
    default=DEFAULT_DB_PATH,
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--prose",
    is_flag=True,
    help="Print prose for a human instead of the default TOON rows.",
)
@click.option(
    # Accepted and ignored: TOON is the default now, but these names are
    # written into agent prompts that predate it, and failing those with
    # "no such option" costs a whole turn to rediscover an unchanged command.
    "--toon",
    "--json-output",
    "--json_output",
    is_flag=True,
    hidden=True,
)
def text_search(
    text: str,
    path: str | None,
    limit: int,
    db_path: str,
    prose: bool,
    toon: bool,  # noqa: ARG001
) -> None:
    """Find the indexed source lines containing TEXT."""
    with ReadOnlyExplorer(db_path) as explorer:
        matches: list[TextMatch] = explorer.find_text_lines(
            text,
            path=path,
            limit=limit,
        )
    if not prose:
        _echo_toon([asdict(match) for match in matches])
        return
    _echo_text_matches(matches)


@explore.command("chunks")
@click.argument("path", required=False)
@click.option("--start-line", "--start_line", type=click.IntRange(min=1))
@click.option("--end-line", "--end_line", type=click.IntRange(min=1))
@click.option(
    "--range",
    "ranges",
    nargs=3,
    multiple=True,
    type=(str, click.IntRange(min=1), click.IntRange(min=1)),
    help="Read PATH START END; repeat to retrieve several ranges in one process.",
)
@click.option(
    "--full",
    is_flag=True,
    help="Print every stored chunk in full instead of an outline.",
)
@click.option(
    "--db-path",
    "--db_path",
    default=DEFAULT_DB_PATH,
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--prose",
    is_flag=True,
    help="Print prose for a human instead of the default TOON rows.",
)
@click.option(
    # Accepted and ignored: TOON is the default now, but these names are
    # written into agent prompts that predate it, and failing those with
    # "no such option" costs a whole turn to rediscover an unchanged command.
    "--toon",
    "--json-output",
    "--json_output",
    is_flag=True,
    hidden=True,
)
def get_chunks(
    path: str | None,
    start_line: int | None,
    end_line: int | None,
    ranges: tuple[tuple[str, int, int], ...],
    full: bool,
    db_path: str,
    prose: bool,
    toon: bool,  # noqa: ARG001
) -> None:
    """Retrieve indexed code from an exact PATH.

    With a line range, the requested source is rebuilt once and printed with
    line numbers. Without one, the path's definitions are listed as an
    outline; pass --full to print every stored chunk instead.

    Source lines always print as numbered text. TOON must quote any value
    holding a colon, and code is full of them, so a table of lines costs
    more than the numbered text it would replace and reads worse.
    """
    if ranges:
        if path is not None or start_line is not None or end_line is not None or full:
            raise click.UsageError(
                "--range cannot be combined with PATH, line options, or --full"
            )
        with ReadOnlyExplorer(db_path) as explorer:
            for index, (range_path, range_start, range_end) in enumerate(ranges):
                if range_start > range_end:
                    raise click.BadParameter(
                        "START cannot be greater than END",
                        param_hint="--range",
                    )
                lines: list[SourceLine] = explorer.get_source_lines(
                    range_path,
                    start_line=range_start,
                    end_line=range_end,
                )
                if index:
                    click.echo()
                _echo_source_lines(lines, path=range_path)
        return
    if path is None:
        raise click.UsageError("Provide PATH or at least one --range PATH START END")
    ranged: bool = start_line is not None or end_line is not None
    try:
        with ReadOnlyExplorer(db_path) as explorer:
            if ranged:
                lines: list[SourceLine] = explorer.get_source_lines(
                    path,
                    start_line=start_line,
                    end_line=end_line,
                )
            elif full:
                chunks: list[IndexedChunk] = explorer.get_chunks(path)
            else:
                entries: list[OutlineEntry] = explorer.get_outline(path)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if ranged:
        _echo_source_lines(lines, path=path)
        return
    if full:
        if not prose:
            _echo_toon([asdict(chunk) for chunk in chunks])
            return
        _echo_chunks(chunks)
        return
    if not prose:
        _echo_toon([asdict(entry) for entry in entries])
        return
    _echo_outline(entries, path=path)
