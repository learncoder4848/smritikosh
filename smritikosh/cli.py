"""smritikosh CLI: index a repo, then search/graph it via hybrid retrieval."""

import click


@click.group()
def main():
    """smritikosh -- codebase indexing and hybrid retrieval."""


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False))
@click.option("--index-dir", default=".smritikosh", help="Directory to store indexes in.")
@click.option("--full", is_flag=True, help="Force a full rebuild instead of an incremental update.")
def index(repo_path: str, index_dir: str, full: bool):
    """Build or incrementally update the index for REPO_PATH."""
    from smritikosh.indexing.pipeline import build_index

    build_index(repo_path, index_dir, incremental=not full)


@main.command()
@click.argument("query")
@click.option("--index-dir", default=".smritikosh", help="Directory indexes were stored in.")
@click.option("--top-k", default=10, help="Number of results to return.")
def search(query: str, index_dir: str, top_k: int):
    """Run a hybrid search QUERY against the built index."""
    from smritikosh.indexing.callgraph_index import CallGraphIndex
    from smritikosh.indexing.lexical_index import LexicalIndex
    from smritikosh.indexing.vector_index import VectorIndex
    from smritikosh.retrieval.hybrid import HybridRetriever

    lexical_index = LexicalIndex(index_dir)
    callgraph_index = CallGraphIndex(index_dir)
    vector_index = VectorIndex(index_dir)
    lexical_index.load()
    callgraph_index.load()
    vector_index.load()

    retriever = HybridRetriever(lexical_index, callgraph_index, vector_index)
    results = retriever.retrieve(query, top_k=top_k)

    for r in results:
        click.echo(f"{r.path}:{r.start_line}-{r.end_line}  score={r.score:.3f}  [{r.source}]")


@main.command()
@click.argument("symbol")
@click.option("--index-dir", default=".smritikosh", help="Directory indexes were stored in.")
@click.option("--direction", type=click.Choice(["callers", "callees"]), default="callers")
def graph(symbol: str, index_dir: str, direction: str):
    """Query the call-graph index for callers/callees of SYMBOL."""
    from smritikosh.indexing.callgraph_index import CallGraphIndex

    callgraph_index = CallGraphIndex(index_dir)
    callgraph_index.load()

    results = (
        callgraph_index.callers_of(symbol)
        if direction == "callers"
        else callgraph_index.callees_of(symbol)
    )
    for r in results:
        click.echo(f"{r.path}:{r.start_line}-{r.end_line}")


if __name__ == "__main__":
    main()
