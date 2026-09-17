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

- [`smritikosh/indexing`](https://github.com/learncoder4848/smritikosh/tree/main/smritikosh/indexing)
  — file router, discovery, parser, extractor, chunker, and pipeline
  orchestration.
- [`smritikosh/engine`](https://github.com/learncoder4848/smritikosh/tree/main/smritikosh/engine)
  — memoization, tracking, batching, and concurrent pipeline helpers.
- [`smritikosh/ports`](https://github.com/learncoder4848/smritikosh/tree/main/smritikosh/ports)
  — file-source, storage, vector-store, and embedder contracts.
- [`smritikosh/adapters`](https://github.com/learncoder4848/smritikosh/tree/main/smritikosh/adapters)
  — local-filesystem, DuckDB, and sentence-transformer implementations of those
  contracts.
- [`smritikosh/retrieval`](https://github.com/learncoder4848/smritikosh/tree/main/smritikosh/retrieval)
  — hybrid candidate fusion, diverse selection, and generic definition and
  dependency expansion.
- [`smritikosh/queries`](https://github.com/learncoder4848/smritikosh/tree/main/smritikosh/queries)
  — packaged tree-sitter tag queries.

The extractor stays under `indexing`: it transforms internal pipeline data
(`ParsedFile -> list[Capture]`) rather than adapting an external system.

## Installation

```bash
pip install smritikosh
```

Or with uv, to get the CLI on your PATH without managing a virtualenv:

```bash
uv tool install smritikosh
```

## Development setup

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

Lock files are not committed. Smritikosh is a library, so installs resolve from
the version ranges in `pyproject.toml`; `uv.lock` and `poetry.lock` are local
artifacts that each tool regenerates on demand.

## Read-only exploration CLI

Two `explore` commands expose the indexed repository to agents without reading
the source tree or taking a DuckDB write lock. `search` finds the ranges worth
reading, and `chunks` reads them:

```bash
smritikosh explore search \
  "authorization decision flow" \
  "authorization failure handling" \
  "authorization tests" \
  --db-path smritikosh.duckdb

smritikosh explore chunks \
  --range src/auth/permissions.py 40 52 \
  --db-path smritikosh.duckdb
```

`search` takes one question as four to eight focused facets. Each facet is
retrieved independently from dense vectors and an incremental Okapi BM25 index,
the two rankings are combined with Reciprocal Rank Fusion, coverage is reserved
for every facet, redundant candidates are dropped, and the survivors are
expanded to complete definitions plus their direct references.

Results come back as [TOON](https://toonformat.dev) — tabular arrays that
declare their columns once and then stream one row each. Facets are labelled by
query id so no row repeats the query text it matched:

```text
queries[3]{id,query}:
  Q1,authorization decision flow
  Q2,authorization failure handling
  Q3,authorization tests
search_results[3]{path,start_line,end_line,symbol,facets}:
  src/auth/permissions.py,59,81,PermissionChecker,Q1|Q2
  src/auth/policy.py,176,193,evaluate,Q1
  tests/auth/test_policy.py,14,38,test_denies_expired_grant,Q3
```

`search` returns locations only. Copy a row's path and line range straight into
`chunks --range PATH START END`, which rebuilds that source once and prints it
with line numbers; repeat `--range` to read several spans in one process.
Without a line range, `chunks PATH` outlines what the file defines instead of
printing it, and `--full` dumps every stored chunk.

`--prose` switches either command to human-readable output. Source lines are
exempt from TOON: it must quote any value containing a colon, so a table of
code lines costs more than the numbered text it would replace.

See [`SEARCH_PIPELINE.md`](SEARCH_PIPELINE.md) for the complete indexing,
retrieval, ranking, expansion, and ports/adapters walkthrough.

Indexes created before hybrid retrieval need one rebuild:

```bash
smritikosh index /path/to/repo --db-path smritikosh.duckdb --full
```

An agent instruction can therefore stay short:

```text
Use the Smritikosh exploration CLI instead of Grep for code discovery.
Run `smritikosh explore search` with focused facets, then
`smritikosh explore chunks --range PATH START END` for the ranges worth reading.
```

## Contributing

See [CONTRIBUTING.md](https://github.com/learncoder4848/smritikosh/blob/main/CONTRIBUTING.md)
for commit and PR conventions.

## Credits

Built by [Shantanu Vashishtha](https://github.com/learncoder4848) and
[Sarvesh Sawant](https://github.com/devsarvesh92).

## Status

Alpha. The pipeline runs end to end — `index` builds an index, `search` and
`explore` query it, and re-indexing is incremental at both the file and the
chunk level. Embedding runs locally on CPU through ONNX Runtime, so the only
network access is a one-time model download.

The CLI surface may still change before 1.0.
