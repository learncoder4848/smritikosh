# smritikosh

Semantic vector search over a codebase.

## Pipeline

**Indexing** — [smritikosh/indexing/pipeline.py](smritikosh/indexing/pipeline.py)

1. [parser.py](smritikosh/indexing/parser.py) -- tree-sitter parse: source files -> AST
2. [extractor.py](smritikosh/indexing/extractor.py) -- symbol extraction
3. [chunker.py](smritikosh/indexing/chunker.py) -- chunking + embedding: code chunks -> vectors
4. [vector_index.py](smritikosh/indexing/vector_index.py) -- semantic similarity

**Search** — `smritikosh search "query"` via [VectorIndex](smritikosh/indexing/vector_index.py)

See [plan/version_1.md](plan/version_1.md) for the v1.0 design.

## Usage

```bash
pip install -e .
smritikosh index /path/to/repo
smritikosh search "query text"
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit and PR conventions.

## Status

Scaffolding only -- pipeline stages and index logic are stubs (`NotImplementedError`)
to be filled in per the v1 plan.
