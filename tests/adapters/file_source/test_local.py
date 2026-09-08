"""Tests for the local filesystem file source."""

from pathlib import Path

from smritikosh.adapters.file_source.local import LocalFileSource


def _write(root: Path, rel: str, text: str = "content") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_should_yield_files_as_sorted_relative_posix_keys(tmp_path: Path) -> None:
    """Sorted so an unchanged tree walks identically every run."""
    for rel in ("src/app.py", "README.md", "src/nested/util.py"):
        _write(tmp_path, rel)

    paths = list(LocalFileSource(str(tmp_path)).iter_paths())

    assert paths == ["README.md", "src/app.py", "src/nested/util.py"]


def test_should_read_file_text_by_relative_key(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py", "import os\n")

    assert LocalFileSource(str(tmp_path)).read_text("src/app.py") == "import os\n"


def test_should_replace_undecodable_bytes_when_reading(tmp_path: Path) -> None:
    (tmp_path / "blob.py").write_bytes(b"valid \xff\xfe tail")

    text = LocalFileSource(str(tmp_path)).read_text("blob.py")

    assert text.startswith("valid ")
    assert text.endswith(" tail")


def test_should_apply_gitignore_patterns(tmp_path: Path) -> None:
    _write(tmp_path, ".gitignore", "secrets/\n*.log\n")

    source = LocalFileSource(str(tmp_path))

    assert source.is_ignored("secrets/key.txt") is True
    assert source.is_ignored("build.log") is True
    assert source.is_ignored("src/app.py") is False


def test_should_ignore_nothing_when_gitignore_absent(tmp_path: Path) -> None:
    assert LocalFileSource(str(tmp_path)).is_ignored("anything.py") is False
