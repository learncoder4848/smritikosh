# smritikosh

Codebase indexing and hybrid retrieval for agent tool calls.

## Pipeline

**Indexing** (build once, then Merkle-diff updates) — [smritikosh/indexing/pipeline.py](smritikosh/indexing/pipeline.py)

1. [parser.py](smritikosh/indexing/parser.py) -- tree-sitter parse: source files -> AST
2. [extractor.py](smritikosh/indexing/extractor.py) -- symbol + call-graph extraction
3. [chunker.py](smritikosh/indexing/chunker.py) -- chunking + embedding: code chunks -> vectors
4. Three indexes built in parallel:
   - [lexical_index.py](smritikosh/indexing/lexical_index.py) -- BM25 identifier/token matches
   - [callgraph_index.py](smritikosh/indexing/callgraph_index.py) -- caller/callee edges
   - [vector_index.py](smritikosh/indexing/vector_index.py) -- semantic similarity

**Retrieval** (per agent call) -- [smritikosh/retrieval/hybrid.py](smritikosh/retrieval/hybrid.py)

`codebase_search` / `codebase_graph` query -> hybrid retrieval (fuse, rerank, dedup via
[rank.py](smritikosh/retrieval/rank.py)) -> ranked results (paths + snippets + scores)

## Usage

```bash
pip install -e .
smritikosh index /path/to/repo
smritikosh search "query text"
smritikosh graph some_function_name --direction callers
```

## Status

Scaffolding only -- pipeline stages and index/retrieval logic are stubs (`NotImplementedError`)
to be filled in.
