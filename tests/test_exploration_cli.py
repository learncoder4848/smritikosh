"""Tests for agent-facing exploration CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import toons
from click.testing import CliRunner

from smritikosh.cli import main
from smritikosh.exploration import (
    IndexInfo,
    OutlineEntry,
    SearchOptions,
    SourceLine,
    TextMatch,
)
from smritikosh.models import SearchResult


def _mock_explorer() -> MagicMock:
    explorer = MagicMock()
    explorer.__enter__.return_value = explorer
    return explorer


def test_should_describe_all_exploration_tools_as_toon() -> None:
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(main, ["explore", "tools", "--toon"])

    # Assert
    assert result.exit_code == 0
    manifest = toons.loads(result.output)
    assert list(manifest["tools"]) == [
        "search",
        "chunks",
        "text",
        "paths",
        "impact",
        "stops",
        "info",
    ]
    assert "loads the embedding model" in manifest["tools"]["search"]
    # The flow is the point of the manifest: one call finds, the next reads.
    assert "--start-line" in manifest["flow"]
    # ...and which of the two retrievers to start from, since a wrong first
    # pick costs a whole round trip.
    assert "Name unknown" in manifest["flow"]


def test_should_emit_toon_without_being_asked_and_ignore_the_pre_toon_flags() -> None:
    # Arrange
    runner = CliRunner()

    # Act
    results = [
        runner.invoke(main, ["explore", "tools", *flag])
        for flag in ([], ["--toon"], ["--json-output"], ["--json_output"])
    ]

    # Assert
    assert [result.exit_code for result in results] == [0, 0, 0, 0]
    assert len({result.output for result in results}) == 1
    assert results[0].output.startswith("version: 3")


def test_should_emit_machine_readable_index_info(tmp_path: Path) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.index_info.return_value = IndexInfo(1, 2, 2, 3)

    # Act
    with patch(
        "smritikosh.exploration_cli.ReadOnlyExplorer",
        return_value=explorer,
    ):
        result = CliRunner().invoke(
            main,
            ["explore", "info", "--db-path", str(db_path), "--toon"],
        )

    # Assert
    assert result.exit_code == 0
    assert toons.loads(result.output) == {
        "files": 1,
        "chunks": 2,
        "vectors": 2,
        "dimensions": 3,
    }


def test_should_forward_multiple_ad_hoc_semantic_queries(tmp_path: Path) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.semantic_search.return_value = [
        SearchResult("src/a.py", 1, 3, "def a(): pass", 0.9, "function")
    ]
    embedder = MagicMock()

    # Act
    with (
        patch(
            "smritikosh.exploration_cli.ReadOnlyExplorer",
            return_value=explorer,
        ),
        patch(
            "smritikosh.exploration_cli.make_embedder",
            return_value=embedder,
        ),
    ):
        result = CliRunner().invoke(
            main,
            [
                "explore",
                "search",
                "first query",
                "refinement",
                "--top-k",
                "5",
                "--exclude-path",
                "tests/%",
                "--db-path",
                str(db_path),
                "--toon",
            ],
        )

    # Assert
    assert result.exit_code == 0
    explorer.semantic_search.assert_called_once_with(
        ["first query", "refinement"],
        embedder=embedder,
        options=SearchOptions(top_k=5, exclude_paths=("tests/%",)),
    )
    assert toons.loads(result.output)[0]["path"] == "src/a.py"


def test_should_omit_snippets_from_toon_results_unless_full_is_requested(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.semantic_search.return_value = [
        SearchResult("src/a.py", 1, 2, "def a():\n    pass", 0.91, "function", "a")
    ]

    # Act
    def run(*extra: str) -> dict[str, object]:
        with (
            patch(
                "smritikosh.exploration_cli.ReadOnlyExplorer",
                return_value=explorer,
            ),
            patch(
                "smritikosh.exploration_cli.make_embedder",
                return_value=MagicMock(),
            ),
        ):
            result = CliRunner().invoke(
                main,
                [
                    "explore",
                    "search",
                    "anything",
                    "--db-path",
                    str(db_path),
                    "--toon",
                    *extra,
                ],
            )
        assert result.exit_code == 0
        return toons.loads(result.output)[0]

    # Assert
    lean = run()
    assert "snippet" not in lean
    assert (lean["path"], lean["start_line"], lean["symbol"]) == ("src/a.py", 1, "a")
    assert run("--full")["snippet"] == "def a():\n    pass"


def test_should_print_locations_without_code_by_default(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.semantic_search.return_value = [
        SearchResult("src/a.py", 1, 2, "def a():\n    pass", 0.91, "function", "a"),
        SearchResult("src/b.py", 7, 9, "def b():\n    pass", 0.72, "function", "b"),
    ]

    # Act
    with (
        patch(
            "smritikosh.exploration_cli.ReadOnlyExplorer",
            return_value=explorer,
        ),
        patch(
            "smritikosh.exploration_cli.make_embedder",
            return_value=MagicMock(),
        ),
    ):
        result = CliRunner().invoke(
            main,
            ["explore", "search", "anything", "--prose", "--db-path", str(db_path)],
        )

    # Assert
    assert result.exit_code == 0
    body: str = result.output.split("\n\n", 1)[1]
    assert body == (
        "src/a.py:1-2  0.910  function  a\nsrc/b.py:7-9  0.720  function  b\n"
    )


def test_should_print_one_line_per_text_match(tmp_path: Path) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.find_text_lines.return_value = [
        TextMatch("src/a.py", 12, "TOTAL = 1", True),
        TextMatch("src/b.py", 5, "TOTAL = 2", False),
    ]

    # Act
    with patch(
        "smritikosh.exploration_cli.ReadOnlyExplorer",
        return_value=explorer,
    ):
        result = CliRunner().invoke(
            main,
            ["explore", "text", "TOTAL", "--prose", "--db-path", str(db_path)],
        )

    # Assert
    assert result.exit_code == 0
    assert result.output == "src/a.py:12: TOTAL = 1\nsrc/b.py:~5: TOTAL = 2\n"


def test_should_print_numbered_source_for_a_requested_line_range(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.get_source_lines.return_value = [
        SourceLine(9, "def total():"),
        SourceLine(10, "    return 1"),
    ]

    # Act
    with patch(
        "smritikosh.exploration_cli.ReadOnlyExplorer",
        return_value=explorer,
    ):
        result = CliRunner().invoke(
            main,
            [
                "explore",
                "chunks",
                "src/a.py",
                "--start-line",
                "9",
                "--end-line",
                "10",
                "--db-path",
                str(db_path),
            ],
        )

    # Assert
    assert result.exit_code == 0
    explorer.get_source_lines.assert_called_once_with(
        "src/a.py",
        start_line=9,
        end_line=10,
    )
    explorer.get_chunks.assert_not_called()
    assert result.output == "src/a.py:9-10\n 9  def total():\n10      return 1\n"


def test_should_outline_the_path_when_no_line_range_is_given(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.get_outline.return_value = [
        OutlineEntry("load_orders", "function", 8, 12),
        OutlineEntry(None, "constant", 100, 140),
    ]

    # Act
    with patch(
        "smritikosh.exploration_cli.ReadOnlyExplorer",
        return_value=explorer,
    ):
        result = CliRunner().invoke(
            main,
            ["explore", "chunks", "src/a.py", "--prose", "--db-path", str(db_path)],
        )

    # Assert
    assert result.exit_code == 0
    explorer.get_chunks.assert_not_called()
    assert result.output == (
        "src/a.py  (2 entries)\n8-12     function  load_orders\n100-140  constant  -\n"
    )


def test_should_print_source_lines_as_numbered_text_even_when_toon_is_asked_for(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.get_source_lines.return_value = [SourceLine(9, "def total():")]

    # Act
    with patch(
        "smritikosh.exploration_cli.ReadOnlyExplorer",
        return_value=explorer,
    ):
        result = CliRunner().invoke(
            main,
            [
                "explore",
                "chunks",
                "src/a.py",
                "--start-line",
                "9",
                "--toon",
                "--db-path",
                str(db_path),
            ],
        )

    # Assert
    assert result.exit_code == 0
    assert result.output == "src/a.py:9-9\n9  def total():\n"


def test_should_print_stored_chunks_when_full_is_requested(tmp_path: Path) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.get_chunks.return_value = []

    # Act
    with patch(
        "smritikosh.exploration_cli.ReadOnlyExplorer",
        return_value=explorer,
    ):
        result = CliRunner().invoke(
            main,
            ["explore", "chunks", "src/a.py", "--full", "--db-path", str(db_path)],
        )

    # Assert
    assert result.exit_code == 0
    explorer.get_chunks.assert_called_once_with("src/a.py")
    explorer.get_outline.assert_not_called()


def test_should_accept_manifest_argument_names_for_semantic_search(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.semantic_search.return_value = []

    # Act
    with (
        patch(
            "smritikosh.exploration_cli.ReadOnlyExplorer",
            return_value=explorer,
        ),
        patch(
            "smritikosh.exploration_cli.make_embedder",
            return_value=MagicMock(),
        ),
    ):
        result = CliRunner().invoke(
            main,
            [
                "explore",
                "search",
                "skip statement generation",
                "--top_k",
                "5",
                "--db_path",
                str(db_path),
                "--toon",
            ],
        )

    # Assert
    assert result.exit_code == 0
    explorer.semantic_search.assert_called_once()
