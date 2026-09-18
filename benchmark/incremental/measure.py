"""Measure what each kind of change costs to re-index.

    python benchmark/incremental/measure.py

Every scenario starts from a byte-identical index, because two things otherwise
distort the result: reverting a file is itself a cache hit — the memo remembers
the earlier content and skips the write, leaving the previous run's chunk nodes
in place — and the first run that embeds anything pays a one-time model load.

The script edits the source tree in place and always restores it.  It never
deletes a real module: the CLI imports them, so the deletion scenario uses a
throwaway file that nothing references.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[2]
TREE = "./smritikosh"

# An ordinary module, processed by the pipeline but not part of it.
PLAIN = "smritikosh/adapters/storage/duckdb.py"
PLAIN_ANCHOR = "Atomically remove all nodes and the file_hash row"

# A module the pipeline itself is built from: its source hash is folded into
# every memo key, so editing it invalidates the memo of every indexed file.
TRACKED = "smritikosh/indexing/pipeline/_pipeline.py"
TRACKED_ANCHOR = "Embed and upsert one chunk;"

SCRATCH = "smritikosh/_bench_scratch.py"
SCRATCH_BODY = '"""Throwaway module, written and deleted by the benchmark."""\n\n\n' + (
    "\n\n".join(
        f'def scratch_{i}(value: int) -> int:\n    """Scratch function {i}."""\n'
        f"    return value * {i}"
        for i in range(1, 7)
    )
)


def run_index(db: Path, *, full: bool = False) -> float:
    """Index the tree into *db* and return wall-clock seconds."""
    cmd = [sys.executable, "-m", "smritikosh", "index", TREE, "--db-path", str(db)]
    if full:
        cmd.append("--full")
    start = time.perf_counter()
    subprocess.run(cmd, cwd=REPO, capture_output=True, check=True)
    return time.perf_counter() - start


def corpus(db: Path) -> tuple[int, int]:
    con = duckdb.connect(str(db), read_only=True)
    files = con.execute("SELECT count(*) FROM file_hashes").fetchone()[0]
    chunk_rows = con.execute("SELECT count(*) FROM nodes WHERE kind = 'chunk'")
    chunks = chunk_rows.fetchone()[0]
    con.close()
    return files, chunks


def chunk_ids(db: Path) -> set[str]:
    con = duckdb.connect(str(db), read_only=True)
    rows = con.execute("SELECT id FROM nodes WHERE kind = 'chunk'").fetchall()
    con.close()
    return {row[0] for row in rows}


@contextmanager
def restored(path: Path):
    """Yield the file's current text, then put it back however the body exits."""
    original = path.read_text()
    try:
        yield original
    finally:
        path.write_text(original)


def in_place(body: str, anchor: str) -> str:
    """Rewrite one docstring without changing the line count."""
    if anchor not in body:
        raise SystemExit(f"anchor not found, update the benchmark: {anchor!r}")
    return body.replace(anchor, f"{anchor} ({uuid.uuid4().hex[:8]})", 1)


def shifted(body: str) -> str:
    """Add two lines near the top, sliding every definition below them."""
    lines = body.split("\n")
    lines.insert(3, f"# bench {uuid.uuid4().hex[:8]}")
    lines.insert(4, "")
    return "\n".join(lines)


def appended(body: str) -> str:
    """Add a definition at the end, leaving every line above it untouched."""
    tag = uuid.uuid4().hex[:8]
    return (
        f'{body}\n\ndef _bench_{tag}() -> None:\n'
        f'    """Added at the end."""\n    return None\n'
    )


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()

    plain, tracked, scratch = REPO / PLAIN, REPO / TRACKED, REPO / SCRATCH
    rows: list[tuple[str, float, str]] = []

    with tempfile.TemporaryDirectory(prefix="smritikosh-bench-") as tmp:
        pristine, work = Path(tmp) / "pristine.duckdb", Path(tmp) / "work.duckdb"

        first_build = run_index(pristine)
        files, chunks = corpus(pristine)
        base = chunk_ids(pristine)
        rows.append(("first build", first_build, f"{chunks} chunks"))

        def measure(name: str, mutate=None, path: Path | None = None) -> None:
            shutil.copyfile(pristine, work)
            if mutate is None:
                elapsed = run_index(work)
            else:
                with restored(path) as original:
                    path.write_text(mutate(original))
                    elapsed = run_index(work)
            embedded = len(chunk_ids(work) - base)
            rows.append((name, elapsed, f"{embedded} of {chunks} chunks"))

        measure("nothing changed")
        measure(
            "one function edited in place",
            lambda b: in_place(b, PLAIN_ANCHOR),
            plain,
        )
        measure("two lines inserted at the top", shifted, plain)
        measure("one function appended at the end", appended, plain)
        measure(
            "the pipeline's own code edited (@sm.tracked)",
            lambda b: in_place(b, TRACKED_ANCHOR),
            tracked,
        )

        # Deletion needs the file indexed first, so it does not fit the loop.
        shutil.copyfile(pristine, work)
        try:
            scratch.write_text(SCRATCH_BODY)
            run_index(work)
            before = corpus(work)[1]
            scratch.unlink()
            elapsed = run_index(work)
            after = corpus(work)[1]
            rows.append(("a file deleted", elapsed, f"{before - after} chunks retired"))
        finally:
            scratch.unlink(missing_ok=True)

        shutil.copyfile(pristine, work)
        rebuild = run_index(work, full=True)
        rows.append(("`--full` rebuild", rebuild, f"{chunks} chunks"))

    print(f"corpus: {files} files, {chunks} chunks\n")
    print("| change | time | embedding work |")
    print("| --- | --- | --- |")
    for name, seconds, work_done in rows:
        print(f"| {name} | {seconds:.1f} s | {work_done} |")


if __name__ == "__main__":
    main()
