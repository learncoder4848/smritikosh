# smritikosh

Semantic vector search over source-code repositories. Smritikosh parses source
files with tree-sitter, identifies meaningful definitions, turns them into
chunks, embeds those chunks, and stores the vectors in DuckDB.

## Pipeline

```text
  FileSource            FileRouter
  (lists + reads)       (extension -> language + strategy)
        |                    |
        +--------> discovery <+        select once, per file
                      |
                      |  3 gates: excluded dirs -> gitignore -> router
                      v
                  SourceFile          path, language, content,
                      |               has_tags_scm, strategy
                      v
        [ file unchanged? ] --yes--> skip file          file_hashes
                      | no
                      v
                   parser              text -> tree-sitter AST
                      v
                  extractor            AST -> definition captures (tags.scm)
                      v
                   chunker             captures -> chunks (ast|section|regex)
                      v
        [ chunk text seen? ] --yes--> reuse vector      content_hash
                      | no
                      v
                  embedder             chunk text -> vector
                      v
                   DuckDB              nodes, vectors, file_hashes, memo_cache
```

Routing happens once, in discovery, and is carried on the `SourceFile`. Later
stages read `language`, `has_tags_scm`, and `strategy` off that object rather
than re-deriving them from the path.

Two skip checks make re-indexing cheap. A file whose SHA-256 is unchanged is
skipped whole. A chunk is keyed by the hash of its own text, so editing one
function in a file re-embeds only that function's chunk.

The extractor uses packaged `tags.scm` queries for Python, Java, Kotlin,
TypeScript, JavaScript, Markdown, and JSON. TOML bypasses extraction and uses
regex chunking. JSON is indexed except for known noise — lockfiles, minified
bundles, and fixture directories.

## Package structure

- [`smritikosh/indexing`](smritikosh/indexing) — file router, discovery, parser,
  extractor, chunker, and pipeline orchestration.
- [`smritikosh/engine`](smritikosh/engine) — memoization, tracking, batching,
  and concurrent pipeline helpers.
- [`smritikosh/ports`](smritikosh/ports) — file-source, storage, vector-store,
  and embedder contracts.
- [`smritikosh/adapters`](smritikosh/adapters) — local-filesystem, DuckDB, and
  sentence-transformer implementations of those contracts.
- [`smritikosh/queries`](smritikosh/queries) — packaged tree-sitter tag queries.

The extractor stays under `indexing`: it transforms internal pipeline data
(`ParsedFile -> list[Capture]`) rather than adapting an external system.

## Design

See the [v1 plan](plan/version_1.md) for the complete design.

## Installation

Both **uv** and **Poetry** are supported. uv is recommended for local development
— it resolves and installs the full dependency tree roughly 5× faster than
Poetry, thanks to a Rust-based resolver and parallel downloads. (Measured on
this project: uv locked 94 packages in ~46 s vs Poetry's ~3.5 min.)

### uv (recommended)

```bash
# Install uv: https://docs.astral.sh/uv/getting-started/installation/
uv sync                  # install deps + project into .venv
uv sync --no-install-project  # deps only (skip the editable install)
```

### Poetry

```bash
# Requires Poetry >= 2.3
poetry install           # install deps + project into .venv
poetry install --no-root # deps only
```

### Running tests

```bash
# uv
uv run pytest

# Poetry / activated venv
make test
```

Both tools create a `.venv` in the project root and share the same `Makefile`
targets. Pass `TOOL=uv` or `TOOL=poetry` to override the default:

```bash
make install TOOL=uv
make lock    TOOL=uv    # regenerates uv.lock
make test               # always uses .venv/bin/python directly
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit and PR conventions.

## Status

The engine, shared models, query files, embedder, DuckDB adapters, chunking
strategies, and capture extractor are implemented. File selection (file source,
router, discovery), tree-sitter parsing, end-to-end pipeline wiring, search, and
the final CLI remain under construction.
