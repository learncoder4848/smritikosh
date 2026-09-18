# What a re-index costs

The figures quoted in the README's [_Why incremental?_](../../README.md#why-incremental)
section. Reproduce them with:

```bash
python benchmark/incremental/measure.py
```

`measure.py` indexes `./smritikosh` into a throwaway database, then replays one kind of
change at a time, each starting from a byte-identical copy of that index. It edits the source
tree in place and always restores it.

## Results

Three consecutive runs on an Apple M4 Max (16 cores), Python 3.14, embeddings computed
locally. Corpus: 59 files, 413 chunks.

| Change | Time | Embedding work |
| --- | --- | --- |
| First build | 36.1 · 37.9 · 47.6 s | 413 chunks |
| Nothing changed | 0.8 · 0.8 · 0.9 s | 0 chunks |
| A file deleted | 0.8 · 0.8 · 0.9 s | 6 chunks retired |
| One function appended at the end | 1.1 · 1.1 · 1.2 s | 1 of 413 chunks |
| One function edited in place | 1.5 · 1.6 · 1.6 s | 4 of 413 chunks |
| Two lines inserted at the top | 3.0 · 3.1 · 3.5 s | 20 of 413 chunks |
| The pipeline's own code edited | 5.8 · 5.8 · 6.2 s | 1 of 413 chunks |
| `--full` rebuild | 38.2 · 40.0 · 42.5 s | 413 chunks |

Chunk counts are deterministic; wall-clock times are not. The first build of the first run is
the slowest entry in the table because the embedding model had not yet been read from disk.

## Reading the table

**Two lines inserted at the top costs more than the same edit made in place.** A chunk's id is
a hash of its path, its line range, *and* its text, so a definition that merely slides down
two lines is a different chunk and is embedded again. Appending to the end of a file is
cheapest for the same reason: nothing above the new definition moves.

**Editing the pipeline's own code re-checks everything and still embeds almost nothing.** The
memo key folds in a hash of every `@sm.tracked` function's source, so changing the chunker
invalidates all 59 files and they are all parsed again — but the chunks they produce are
unchanged, so the vector store already has them and the embedder is never called. The two
tiers of caching are independent, and this row is where you can see both.

**Swapping the embedding model costs a full rebuild**, because `EMBEDDER` is a
`detect_change=True` context key and old vectors are not comparable to new ones. That is the
`--full` row.

## Two ways to measure this wrong

Both cost real time to discover, so they are worth stating.

*Reverting a file is itself a cache hit.* `process_file` is memoized, so writing back content
that was indexed earlier in the session skips the function entirely — including its writes.
The chunk nodes from the mutated version stay in the database, and a baseline captured
afterwards is not the baseline you think it is. `measure.py` copies a pristine database for
every scenario instead of reverting.

*The first run that embeds anything pays a one-time model load.* Roughly four seconds on this
machine, which is larger than most of the numbers in the table. A no-op run never loads the
model at all, so it cannot be used to warm it.
