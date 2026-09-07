"""Indexing pipeline orchestrator: repo -> parse -> extract -> chunk/embed -> 3 indexes.

Build once, then Merkle-diff updates on subsequent runs.
"""

from smritikosh.indexing import chunker, extractor, parser
from smritikosh.indexing.callgraph_index import CallGraphIndex
from smritikosh.indexing.lexical_index import LexicalIndex
from smritikosh.indexing.vector_index import VectorIndex


def compute_repo_hash(repo_path: str) -> dict[str, str]:
    """Compute a Merkle-tree-style hash per file (or subtree) for diffing.

    TODO: hash file contents, roll up into directory hashes.
    """
    raise NotImplementedError


def diff_changed_files(old_hashes: dict[str, str], new_hashes: dict[str, str]) -> list[str]:
    """Compare two hash trees and return paths that changed/were added/removed.

    TODO: implement Merkle diff.
    """
    raise NotImplementedError


def build_index(repo_path: str, index_dir: str, incremental: bool = True) -> None:
    """Run the full indexing pipeline.

    incremental=True: use Merkle-diff to only reprocess changed files.
    incremental=False: rebuild everything from scratch.

    TODO: wire this together, e.g.:
      1. determine files to (re)process (compute_repo_hash + diff_changed_files)
      2. for each file: parser.parse_file -> extractor.extract_* -> chunker.chunk_file/embed_chunks
      3. update LexicalIndex, CallGraphIndex, VectorIndex
      4. persist new hash tree + all three indexes
    """
    raise NotImplementedError
