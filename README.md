# smritikosh

Semantic vector search over source-code repositories. Smritikosh parses source
files with tree-sitter, identifies meaningful definitions, turns them into
chunks, embeds those chunks, and stores the vectors in DuckDB.

## Pipeline

```text
Source files
  -> parser: source text to tree-sitter AST
  -> extractor: AST to named definition captures
  -> chunker: captures to searchable code chunks
  -> embedder: chunks to vectors
  -> storage: metadata and vectors in DuckDB
```

The extractor uses packaged `tags.scm` queries for Python, Java, Kotlin,
TypeScript, JavaScript, Markdown, and JSON. TOML bypasses extraction and will
use regex chunking.

## Package structure

- [`smritikosh/indexing`](smritikosh/indexing) — parser, extractor, chunker, and
  pipeline orchestration.
- [`smritikosh/engine`](smritikosh/engine) — memoization, tracking, batching,
  and concurrent pipeline helpers.
- [`smritikosh/ports`](smritikosh/ports) — storage, vector-store, and embedder
  contracts.
- [`smritikosh/adapters`](smritikosh/adapters) — DuckDB and sentence-transformer
  implementations of those contracts.
- [`smritikosh/queries`](smritikosh/queries) — packaged tree-sitter tag queries.

The extractor stays under `indexing`: it transforms internal pipeline data
(`ParsedFile -> list[Capture]`) rather than adapting an external system.

## Design

See the [v1 plan](plan/version_1.md) and implemented story LLDs:

- [Embedding and vector storage](plan/lld/ICCSVC-8915.md)
- [Tree-sitter query files](plan/lld/ICCSVC-8916.md)
- [Capture extractor](plan/lld/ICCSVC-8922.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit and PR conventions.

## Status

The engine, shared models, query files, embedder, DuckDB adapters, and capture
extractor are implemented. Parser routing, chunking, end-to-end pipeline wiring,
search, and the final CLI remain under construction.
