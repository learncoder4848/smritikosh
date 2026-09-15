"""CLI commands for read-only, agent-driven index exploration."""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Final, cast

import click
import toons

from smritikosh.adapters.embedder import make_embedder
from smritikosh.constants import DEFAULT_DB_PATH
from smritikosh.exploration import (
    GraphDirection,
    ImpactEntry,
    IndexedChunk,
    OutlineEntry,
    ReadOnlyExplorer,
    SearchOptions,
    SourceLine,
    TextMatch,
    UnresolvedReference,
)
from smritikosh.models import SearchResult

__all__ = ["explore"]

TOOL_MANIFEST: Final[dict[str, object]] = {
    "version": 3,
    "flow": (
        "Name unknown, meaning known: search. Name known, want what connects "
        "to it: impact. search returns locations; read one with "
        "chunks PATH --start-line N --end-line M. Two calls answer most "
        "questions."
    ),
    # One line per tool: the manifest is read by an agent on every session, so
    # its own size is a cost, and nested argument tables cost more than they
    # explain about a command whose usage string already names its options.
    "tools": {
        "search": (
            "explore search QUERY... [--top-k N] [--include-path LIKE] "
            "[--exclude-path LIKE] [--full] — code by meaning; reports "
            "locations, not code; loads the embedding model"
        ),
        "chunks": (
            "explore chunks PATH [--start-line N] [--end-line M] [--full] — "
            "outline a file, or print its source for a line range"
        ),
        "text": (
            "explore text TEXT [--path PATH] [--limit N] — exact symbol or "
            "string, as path:line: line"
        ),
        "paths": "explore paths PATTERN [--limit N] — paths containing a substring",
        "impact": (
            "explore impact SYMBOL [--direction in|out] [--depth N] "
            "[--min-confidence F] — what breaks if SYMBOL changes (in) or what "
            "it reaches (out); reports symbols, not code"
        ),
        "stops": (
            "explore stops [--path PATH] — calls no indexed definition "
            "satisfies, so an empty impact is distinguishable from a gap"
        ),
        "info": "explore info — index size and embedding dimensions",
    },
    "notes": (
        "Prefix every command with `smritikosh `. Output is TOON; --prose "
        "switches to prose. All but tools take --db-path INDEX. Source "
        "lines print as numbered text either way. impact reports locations; "
        "read the ones that matter with chunks rather than all of them."
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


def _echo_impact(
    entries: list[ImpactEntry],
    *,
    symbol: str,
    direction: str,
) -> None:
    if not entries:
        click.echo(
            f"No symbols {'reach' if direction == 'in' else 'reached by'} "
            f"{symbol}. Check `explore stops` — the call may be unresolved "
            "rather than absent."
        )
        return
    verb: str = "reaching" if direction == "in" else "reached by"
    click.echo(f"{len(entries)} symbol(s) {verb} {symbol}:\n")
    for entry in entries:
        # "?" marks a hop that rested on an ambiguous name, so a reader can
        # tell a certain caller from a plausible one without reading the code.
        marker: str = "" if entry.confidence >= 1.0 else "  ?"
        click.echo(
            f"depth {entry.depth}  {entry.symbol}  "
            f"{entry.path}:{entry.start_line}-{entry.end_line}{marker}"
        )


def _echo_unresolved(references: list[UnresolvedReference]) -> None:
    if not references:
        click.echo("No unresolved calls.")
        return
    for reference in references:
        source: str = reference.src_symbol or "-"
        click.echo(
            f"{reference.path}:{reference.line}: {source} -> "
            f'"{reference.name}" not defined in this index'
        )


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


def _result_payload(result: SearchResult, *, full: bool) -> dict[str, object]:
    """Serialize one hit, carrying its code only when it was asked for."""
    payload: dict[str, object] = asdict(result)
    # Cosine scores separate hits in the third decimal at most; the float's
    # remaining sixteen digits are tokens spent on noise.
    payload["score"] = round(result.score, 3)
    if not full:
        del payload["snippet"]
    return payload


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
) -> None:
    if not results:
        click.echo(f"No results found.  ({elapsed_ms:.0f} ms)")
        return
    click.echo(f"Found {len(results)} result(s) in {elapsed_ms:.0f} ms:\n")
    for result in results:
        _echo_location(result)
        # Code is what `chunks --start-line` is for. Shipping it with every
        # hit was three quarters of a search result, and a caller that means
        # to read one of them pays for the other four.
        if full:
            for line in result.snippet.splitlines():
                click.echo(f"    {line}")
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
def list_tools(prose: bool, toon: bool) -> None:  # noqa: ARG001
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
    elapsed_ms: float = (time.perf_counter() - started_at) * 1000
    if not prose:
        _echo_toon([_result_payload(result, full=full) for result in results])
        return
    _echo_results(results, elapsed_ms=elapsed_ms, full=full)


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


@explore.command("impact")
@click.argument("symbol")
@click.option(
    "--direction",
    type=click.Choice(["in", "out"]),
    default="in",
    show_default=True,
    help="in: what reaches SYMBOL.  out: what SYMBOL reaches.",
)
@click.option("--depth", default=1, show_default=True, type=click.IntRange(min=1))
@click.option(
    "--min-confidence",
    "--min_confidence",
    default=0.0,
    show_default=True,
    type=click.FloatRange(min=0.0, max=1.0),
    help="Drop hops resting on an ambiguous name; 1.0 keeps only certain ones.",
)
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
def impact(
    symbol: str,
    direction: str,
    depth: int,
    min_confidence: float,
    limit: int,
    db_path: str,
    prose: bool,
) -> None:
    """Report what changing SYMBOL affects, or what it depends on.

    Symbols only, never their code — the point is to narrow a long list before
    reading anything. Read the ones that matter with
    `chunks PATH --start-line N --end-line M`.
    """
    try:
        with ReadOnlyExplorer(db_path) as explorer:
            entries: list[ImpactEntry] = explorer.impact(
                symbol,
                direction=GraphDirection(direction),
                depth=depth,
                min_confidence=min_confidence,
                limit=limit,
            )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if not prose:
        _echo_toon([asdict(entry) for entry in entries])
        return
    _echo_impact(entries, symbol=symbol, direction=direction)


@explore.command("stops")
@click.option("--path", help="Restrict results to one exact indexed path.")
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
def stops(path: str | None, limit: int, db_path: str, prose: bool) -> None:
    """List calls that no indexed definition satisfies.

    Mostly standard-library and third-party calls the index has no reason to
    know. Reporting them is what makes an empty `impact` result readable: the
    graph stopped here, rather than nothing being there.
    """
    try:
        with ReadOnlyExplorer(db_path) as explorer:
            references: list[UnresolvedReference] = explorer.unresolved_references(
                path=path,
                limit=limit,
            )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if not prose:
        _echo_toon([asdict(reference) for reference in references])
        return
    _echo_unresolved(references)


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
@click.argument("path")
@click.option("--start-line", "--start_line", type=click.IntRange(min=1))
@click.option("--end-line", "--end_line", type=click.IntRange(min=1))
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
    path: str,
    start_line: int | None,
    end_line: int | None,
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
