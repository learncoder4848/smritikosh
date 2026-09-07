"""smritikosh CLI: index a repo, then search via vector similarity."""

import click


@click.group()
def main():
    """smritikosh -- semantic vector search over a codebase."""


@main.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--index-dir", default=".smritikosh", help="Directory to store indexes in."
)
@click.option(
    "--full",
    is_flag=True,
    help="Force a full rebuild instead of an incremental update.",
)
def index(repo_path: str, index_dir: str, full: bool):
    """Build or incrementally update the index for REPO_PATH."""
    from smritikosh.indexing.pipeline import build_index

    build_index(repo_path, index_dir, incremental=not full)


@main.command()
@click.argument("query")
@click.option(
    "--index-dir", default=".smritikosh", help="Directory indexes were stored in."
)
@click.option("--top-k", default=10, help="Number of results to return.")
def search(query: str, index_dir: str, top_k: int):
    """Run a semantic search QUERY against the built vector index."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
