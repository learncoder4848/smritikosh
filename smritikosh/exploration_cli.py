"""CLI commands for read-only, agent-driven index exploration."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Final, cast

import click

from smritikosh.adapters.embedder import make_embedder
from smritikosh.constants import DEFAULT_DB_PATH
from smritikosh.exploration import IndexedChunk, ReadOnlyExplorer, SearchOptions
from smritikosh.models import SearchResult

__all__ = ["explore"]

TOOL_MANIFEST: Final[dict[str, object]] = {
    "version": 1,
    "workflow": [
        "Use search first for conceptual code discovery.",
        "Use chunks to inspect the strongest production result.",
        "Use text to resolve exact symbols or constants.",
        "Use paths when only part of a filename is known.",
        "Use info only to verify index availability or size.",
    ],
    "tools": [
        {
            "name": "search",
            "purpose": "Find indexed code by meaning.",
            "command": "smritikosh explore search QUERY...",
            "arguments": {
                "queries": "One or more natural-language queries.",
                "top_k": "Maximum number of merged results.",
                "include_path": "Optional SQL LIKE path patterns.",
                "exclude_path": "Optional SQL LIKE path patterns to exclude.",
                "db_path": "Path to the Smritikosh DuckDB index.",
            },
            "loads_model": True,
            "next_steps": ["chunks", "text"],
        },
        {
            "name": "chunks",
            "purpose": "Retrieve indexed code from one exact path.",
            "command": "smritikosh explore chunks PATH",
            "arguments": {
                "path": "Exact indexed source path.",
                "start_line": "Optional first overlapping source line.",
                "end_line": "Optional last overlapping source line.",
                "db_path": "Path to the Smritikosh DuckDB index.",
            },
            "loads_model": False,
            "next_steps": ["text"],
        },
        {
            "name": "text",
            "purpose": "Find an exact symbol or phrase in indexed chunks.",
            "command": "smritikosh explore text TEXT",
            "arguments": {
                "text": "Case-insensitive text to locate.",
                "path": "Optional exact indexed source path.",
                "limit": "Maximum number of matching chunks.",
                "db_path": "Path to the Smritikosh DuckDB index.",
            },
            "loads_model": False,
            "next_steps": ["chunks"],
        },
        {
            "name": "paths",
            "purpose": "Find indexed paths containing a substring.",
            "command": "smritikosh explore paths PATTERN",
            "arguments": {
                "pattern": "Case-insensitive path substring.",
                "limit": "Maximum number of matching paths.",
                "db_path": "Path to the Smritikosh DuckDB index.",
            },
            "loads_model": False,
            "next_steps": ["chunks", "text"],
        },
        {
            "name": "info",
            "purpose": "Report index size and embedding dimensions.",
            "command": "smritikosh explore info",
            "arguments": {
                "db_path": "Path to the Smritikosh DuckDB index.",
            },
            "loads_model": False,
            "next_steps": ["search"],
        },
    ],
}


def _echo_json(value: object) -> None:
    click.echo(json.dumps(value, indent=2))


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


def _echo_results(results: list[SearchResult], *, elapsed_ms: float) -> None:
    if not results:
        click.echo(f"No results found.  ({elapsed_ms:.0f} ms)")
        return
    click.echo(f"Found {len(results)} result(s) in {elapsed_ms:.0f} ms:\n")
    for result in results:
        kind: str = f"  [{result.chunk_kind}]" if result.chunk_kind else ""
        click.echo(
            f"{result.path}:{result.start_line}-{result.end_line}  "
            f"score={result.score:.3f}{kind}"
        )
        for line in result.snippet.splitlines():
            click.echo(f"    {line}")
        click.echo()


@click.group()
def explore() -> None:
    """Explore an existing index through read-only agent-friendly commands."""


@explore.command("tools")
@click.option(
    "--json-output",
    "--json_output",
    is_flag=True,
    help="Emit machine-readable JSON.",
)
def list_tools(json_output: bool) -> None:
    """Describe exploration commands and the recommended agent workflow."""
    if json_output:
        _echo_json(TOOL_MANIFEST)
        return
    tools: list[dict[str, object]] = cast(
        list[dict[str, object]], TOOL_MANIFEST["tools"]
    )
    for tool in tools:
        click.echo(f"{tool['name']}: {tool['purpose']}")
        click.echo(f"  {tool['command']}")


@explore.command("info")
@click.option(
    "--db-path",
    "--db_path",
    default=DEFAULT_DB_PATH,
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--json-output",
    "--json_output",
    is_flag=True,
    help="Emit machine-readable JSON.",
)
def index_info(db_path: str, json_output: bool) -> None:
    """Show indexed file, chunk, vector, and dimension counts."""
    with ReadOnlyExplorer(db_path) as explorer:
        info = explorer.index_info()
    if json_output:
        _echo_json(asdict(info))
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
    "--db-path",
    "--db_path",
    default=DEFAULT_DB_PATH,
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--json-output",
    "--json_output",
    is_flag=True,
    help="Emit machine-readable JSON.",
)
def semantic_search(
    queries: tuple[str, ...],
    top_k: int,
    include_path: tuple[str, ...],
    exclude_path: tuple[str, ...],
    db_path: str,
    json_output: bool,
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
    elapsed_ms: float = (time.perf_counter() - started_at) * 1000
    if json_output:
        _echo_json([asdict(result) for result in results])
        return
    _echo_results(results, elapsed_ms=elapsed_ms)


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
    "--json-output",
    "--json_output",
    is_flag=True,
    help="Emit machine-readable JSON.",
)
def find_paths(pattern: str, limit: int, db_path: str, json_output: bool) -> None:
    """Find indexed paths containing PATTERN."""
    with ReadOnlyExplorer(db_path) as explorer:
        paths: list[str] = explorer.find_paths(pattern, limit=limit)
    if json_output:
        _echo_json(paths)
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
    "--json-output",
    "--json_output",
    is_flag=True,
    help="Emit machine-readable JSON.",
)
def text_search(
    text: str,
    path: str | None,
    limit: int,
    db_path: str,
    json_output: bool,
) -> None:
    """Find indexed chunks containing TEXT."""
    with ReadOnlyExplorer(db_path) as explorer:
        chunks: list[IndexedChunk] = explorer.text_search(
            text,
            path=path,
            limit=limit,
        )
    if json_output:
        _echo_json([asdict(chunk) for chunk in chunks])
        return
    _echo_chunks(chunks)


@explore.command("chunks")
@click.argument("path")
@click.option("--start-line", "--start_line", type=click.IntRange(min=1))
@click.option("--end-line", "--end_line", type=click.IntRange(min=1))
@click.option(
    "--db-path",
    "--db_path",
    default=DEFAULT_DB_PATH,
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--json-output",
    "--json_output",
    is_flag=True,
    help="Emit machine-readable JSON.",
)
def get_chunks(
    path: str,
    start_line: int | None,
    end_line: int | None,
    db_path: str,
    json_output: bool,
) -> None:
    """Retrieve chunks from an exact indexed PATH."""
    try:
        with ReadOnlyExplorer(db_path) as explorer:
            chunks: list[IndexedChunk] = explorer.get_chunks(
                path,
                start_line=start_line,
                end_line=end_line,
            )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        _echo_json([asdict(chunk) for chunk in chunks])
        return
    _echo_chunks(chunks)
