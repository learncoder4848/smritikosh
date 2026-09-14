"""Tests for agent-facing exploration CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from smritikosh.cli import main
from smritikosh.exploration import IndexInfo, SearchOptions
from smritikosh.models import SearchResult


def _mock_explorer() -> MagicMock:
    explorer = MagicMock()
    explorer.__enter__.return_value = explorer
    return explorer


def test_should_describe_all_exploration_tools_as_json() -> None:
    # Arrange
    runner = CliRunner()

    # Act
    result = runner.invoke(main, ["explore", "tools", "--json-output"])

    # Assert
    assert result.exit_code == 0
    manifest = json.loads(result.output)
    assert [tool["name"] for tool in manifest["tools"]] == [
        "search",
        "chunks",
        "text",
        "paths",
        "info",
    ]
    assert manifest["tools"][0]["loads_model"] is True


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
            ["explore", "info", "--db-path", str(db_path), "--json-output"],
        )

    # Assert
    assert result.exit_code == 0
    assert json.loads(result.output) == {
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
                "--json-output",
            ],
        )

    # Assert
    assert result.exit_code == 0
    explorer.semantic_search.assert_called_once_with(
        ["first query", "refinement"],
        embedder=embedder,
        options=SearchOptions(top_k=5, exclude_paths=("tests/%",)),
    )
    assert json.loads(result.output)[0]["path"] == "src/a.py"


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
                "--json_output",
            ],
        )

    # Assert
    assert result.exit_code == 0
    explorer.semantic_search.assert_called_once()
