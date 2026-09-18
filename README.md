<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/hero-light.svg">
  <img src="assets/hero-light.svg" alt="Git repositories, whether one monorepo or many, plus documents and Slack threads, stay live as they change, and the list keeps growing &mdash; more sources you can ask for are on the way. Smritikosh keeps them in sync incrementally, re-reading only the delta and leaving everything else untouched, then hands a coding agent a handful of exact source ranges &mdash; from either repository, from a document, or from a Slack thread &mdash; that never point at a stale line number. Keywords: incremental sync, always-fresh context, semantic code search, hybrid retrieval, agent memory, exact citations, local-first RAG." width="100%" draggable="false"></picture>

# Your agents deserve _exact evidence._

**Star us ❤️ →** [Smritikosh on GitHub](https://github.com/learncoder4848/smritikosh) ·
[PyPI](https://pypi.org/project/smritikosh/) ·
[Benchmarks](#benchmarks) ·
[Issues](https://github.com/learncoder4848/smritikosh/issues) ·
[Contributing](CONTRIBUTING.md)

Smritikosh is a local-first indexing and retrieval tool for code, documents, and conversations.
It incrementally indexes changes and returns precise, line-cited passages for agents—without
API keys, hosted vector databases, or sending source data off-device.

**Precise** · line-level citations &nbsp;·&nbsp; **Incremental** · indexes only changes &nbsp;·&nbsp; **Local** · no API keys or cloud

[![CI](https://github.com/learncoder4848/smritikosh/actions/workflows/ci.yml/badge.svg)](https://github.com/learncoder4848/smritikosh/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/smritikosh?color=4C8DFF)](https://pypi.org/project/smritikosh/)
[![Downloads](https://img.shields.io/pypi/dm/smritikosh?color=34D399)](https://pypi.org/project/smritikosh/)
[![Python 3.10–3.13](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)](https://www.python.org/)
[![Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)

</div>

## Get started

No Python on the machine? `uv` brings its own.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # Windows: docs.astral.sh/uv
uv tool install smritikosh
```

Or `pipx install smritikosh`. Where the command is missing from PATH, `python -m smritikosh`
is the same thing.

**Index whatever the agent should know.** It all lands in one `./smritikosh.duckdb` and is
searched as a single corpus.

```bash
smritikosh index ./auth-svc        # one repository, or fifty — repeat per repo
smritikosh index ./docs            # Markdown and MDX beside the code
smritikosh index ./slack-export    # Slack threads and .docx — soon
```

**Then let the agent explore.** `explore tools` hands it the workflow and the citation
contract, `search` returns locations, `chunks` reads only those ranges.

```bash
smritikosh explore tools
smritikosh explore search "authorization decision flow" "authorization tests"
smritikosh explore chunks --range src/auth/policy.py 176 193
```

Re-run `index` anytime — unchanged files are skipped, so only the Δ costs anything.
Add `--watch` to keep it live while you work.

## Retrieval — _evidence you can point at_

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/hybrid-retrieval-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/hybrid-retrieval-light.svg">
  <img src="assets/hybrid-retrieval-light.svg" alt="An agent asks one plain question, why can't users log in, and Smritikosh turns it into four angles: where login is decided, what it checks, where it says no, and the tests that cover it. Each angle runs down three retrieval channels: semantic recall over dense vectors, lexical precision over BM25, and a call-graph channel that is not yet implemented. The rankings are combined by Reciprocal Rank Fusion, Facet Reservation, and Maximal Marginal Relevance, and what survives comes back as a short list of exact line ranges such as auth/policy.py 176-193: whole definitions plus one hop further, with line numbers that stay true." width="100%" draggable="false"></picture>

Ask _why can't users log in?_ and Smritikosh looks at it from four sides: where the decision
is made, what it checks, where it says no, and the tests that cover it.

It matches the idea _and_ the exact names, keeps an answer from every side, drops
near-copies, and widens each one to the whole thought plus one place that refers to it —
so what comes back is the exact lines, not everything around them.

## Why _incremental?_

Your agent is only as good as the lines it can trust. Code moves all day, and an index that
doesn't move with it quietly points at the wrong ones. Smritikosh keeps up — and only ever
re-reads what changed.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/incremental-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/incremental-light.svg">
  <img src="assets/incremental-light.svg" alt="Why an index has to keep up. Before: in the file policy.py, the login check sits at lines 176 to 193. Then someone adds two new lines near the top of that file, and everything below them moves down, so the login check now sits at lines 178 to 195. An index that was not updated still answers lines 176 to 193: that answer is instant, it is two lines too high, and it quotes the wrong code. Smritikosh notices the file changed, reads that one file again in 3 seconds, and answers lines 178 to 195. Leave smritikosh index with the watch flag running and it keeps up on every save; re-reading all 59 files in the project instead would take 40 seconds. Keywords: stale index, line numbers moved, exact citations, incremental update, watch mode, always fresh." width="100%" draggable="false"></picture>

## Benchmarks

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/benchmarks-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/benchmarks-light.svg">
  <img src="assets/benchmarks-light.svg" alt="Recorded session cost by benchmark task: production triage 0.381 dollars with Smritikosh versus 1.634 reading the repository directly, interest computation 0.230 versus 0.330, architecture discovery 0.361 versus 1.259. Lower is better." width="100%" draggable="false"></picture>

Paired agent sessions, same question and same effective model per pair:

| Task | Smritikosh | Baseline | Effect |
| --- | --- | --- | --- |
| [Multi-repo production triage](benchmark/multi-repo/production-triage/concise-smritikosh-vs-direct-exploration.canvas.tsx) | 105.3 s · $0.381 | 193.4 s · $1.634 | 45.6% faster · 76.7% cheaper · 90.0% fewer tokens |
| [Single-repo interest computation](benchmark/single-repo/interest-computation-smritikosh-vs-direct.canvas.tsx) | 68.4 s · $0.230 | 55.8 s · $0.330 | 30.4% cheaper · 32.5% fewer tokens · 40% fewer tool calls |
| [Curated architecture discovery](benchmark/docs/ibiza-smritikosh-vs-selective-loading.canvas.tsx) | 56.6 s · $0.361 | 113.9 s · $1.259 | 50.3% faster · 71.3% cheaper · 80.4% fewer tokens |

These are individual exported sessions, not statistically controlled measurements, and
cumulative token counts include repeated cache reads. The artifacts deliberately record where
each answer fell short — the interest run was 12.6 seconds slower, and the triage baseline
covered more repositories — so the efficiency numbers can be read honestly.

## What Smritikosh offers

| | |
| --- | --- |
| **One index, many sources** | Point `index` at each repository and docs tree in turn; they share one database and are searched as a single corpus. A production-triage assistant can trace ownership, events, gates, and failure paths, and an answer can cite two services and a design doc at once. |
| **Agent-ready exploration** | `explore tools` teaches the model how to search, verify, cite, and stop. `search` finds candidates, `chunks` reads only the selected ranges, so a code-aware agent can retrieve the exact implementation and its tests before answering. |
| **Hybrid search** | Dense vectors for meaning, BM25 for identifiers, RRF for fusion, Facet Reservation for coverage, MMR for diversity — the retrieval a repository Q&A needs so every citation points back to the precise range used as evidence. |
| **Definition-aligned evidence** | Tree-sitter queries keep classes, functions, and methods whole, so a range is always a complete thought. Architecture discovery tools map those definitions and their direct references without loading whole repositories into context. |
| **Δ incremental re-indexing** | SHA-256 file skipping, chunk-level memoization keyed on content *and* on the code that produced it, stale-chunk retirement, optional `--watch`. |
| **Local and read-only** | Source, metadata, vectors, BM25 postings, and incremental state live in one DuckDB file. Exploration never takes a write lock or touches the source tree — offline developer tooling, with no source sent to a hosted service. |
| **Multi-language** | AST-aware indexing for Python, TypeScript, JavaScript, Java, and Kotlin; structure-aware strategies for Markdown, MDX, JSON, and TOML. |

## How it works

Indexing is a four-step walk onto one DuckDB file. Search is the reverse: a question hits
those indexes, then comes back as a handful of line ranges.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/how-it-works-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/how-it-works-light.svg">
  <img src="assets/how-it-works-light.svg" alt="How Smritikosh works. It walks the tree, skipping gitignored files and routing each remaining file by language. It parses the file, extracts whole definitions, and chunks them so a function stays a function. Each chunk is stored three ways in one local DuckDB persistence layer: dense vectors for meaning, BM25 for exact names, and a call-graph channel that is not yet implemented. Chunks, metadata, vectors, BM25 postings, and incremental hash-and-memo state share that same DuckDB file. On later runs only files whose content hash changed re-enter the expensive stages. Search then returns exact PATH start-end ranges." width="100%" draggable="false"></picture>

**1. Walk the tree.** Discovery respects `.gitignore`, then the language router sends each
file to the right parser — Python, TypeScript, JavaScript, Java, Kotlin, Markdown, and a
few structured formats.

**2. Keep whole thoughts.** Parse the AST, extract classes / functions / methods, then
chunk so a citation is never the tail of one function and the head of the next.

**3. Index three ways.** The same chunks land in dense vectors (meaning) and BM25 (exact
names) inside one local DuckDB file. A call-graph channel — callers and callees — is next.

**4. Re-read only Δ.** A content hash decides whether a file is touched at all. Unchanged
chunks keep the vectors they already have. Add `--watch` and this happens as you save.

**5. Persist locally.** Chunks, metadata, dense vectors, BM25 postings, and incremental
state live in one `smritikosh.duckdb` — the same file search reads.

Ask a question and [hybrid retrieval](#retrieval--evidence-you-can-point-at) fuses those
rankings, keeps one hit per angle, drops near-duplicates, and expands survivors to complete
definitions plus one reference hop — then returns `PATH START-END`, never the file body.

| Package | Job |
| --- | --- |
| [`smritikosh/indexing`](smritikosh/indexing) | Discover files, parse, extract, chunk, orchestrate the pipeline |
| [`smritikosh/queries`](smritikosh/queries) | Tree-sitter tag queries per language |
| [`smritikosh/engine`](smritikosh/engine) | Memoization, change tracking, batching, concurrency |
| [`smritikosh/ports`](smritikosh/ports) | Contracts for file source, storage, vectors, and embedders |
| [`smritikosh/adapters`](smritikosh/adapters) | Local filesystem, DuckDB, and embedding implementations |
| [`smritikosh/retrieval`](smritikosh/retrieval) | Fuse candidates, keep coverage, expand definitions |

Indexes built before hybrid retrieval need one rebuild:

```bash
smritikosh index /path/to/repo --db-path smritikosh.duckdb --full
```

Built by [Shantanu Vashishtha](https://github.com/learncoder4848) and
[Sarvesh Sawant](https://github.com/devsarvesh92).

<div align="center">

Apache 2.0 · © Smritikosh contributors

</div>
