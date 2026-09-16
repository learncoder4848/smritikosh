"""Tests for agent-facing exploration CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import toons
from click.testing import CliRunner

from smritikosh.cli import main
from smritikosh.exploration import (
    IndexedChunk,
    IndexInfo,
    OutlineEntry,
    SearchOptions,
    SourceLine,
    TextMatch,
)
from smritikosh.models import EvidencePack, SearchResult


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
        "info",
        "batch",
        "evidence",
    ]
    assert "loads the embedding model" in manifest["tools"]["search"]
    assert "run evidence" in manifest["flow"]


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
    assert results[0].output.startswith("version: 5")


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


def test_should_include_numbered_source_context_with_search_results(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.semantic_search.return_value = [
        SearchResult("src/a.py", 3, 4, "def a():\n    pass", 0.91, "function", "a")
    ]
    explorer.get_source_lines.return_value = [
        SourceLine(1, "import os"),
        SourceLine(2, ""),
        SourceLine(3, "def a():"),
        SourceLine(4, "    pass"),
        SourceLine(5, ""),
        SourceLine(6, "TOTAL = 1"),
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
            [
                "explore",
                "search",
                "anything",
                "--context",
                "2",
                "--db-path",
                str(db_path),
            ],
        )

    # Assert
    assert result.exit_code == 0
    explorer.get_source_lines.assert_called_once_with(
        "src/a.py",
        start_line=1,
        end_line=6,
    )
    payload = toons.loads(result.output)[0]
    assert payload["context"] == (
        "1  import os\n2  \n3  def a():\n4      pass\n5  \n6  TOTAL = 1"
    )


def test_should_read_multiple_source_ranges_with_one_chunks_command(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.get_source_lines.side_effect = [
        [SourceLine(1, "first")],
        [SourceLine(7, "second")],
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
                "--range",
                "src/a.py",
                "1",
                "2",
                "--range",
                "src/b.py",
                "7",
                "8",
                "--db-path",
                str(db_path),
            ],
        )

    # Assert
    assert result.exit_code == 0
    assert explorer.get_source_lines.call_count == 2
    assert result.output == ("src/a.py:1-1\n1  first\n\nsrc/b.py:7-7\n7  second\n")


def test_should_reuse_explorer_and_embedder_for_batch_requests(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.semantic_search.return_value = [
        SearchResult("src/a.py", 1, 2, "def a():\n    pass", 0.9, "function", "a")
    ]
    explorer.get_source_lines.return_value = [SourceLine(1, "def a():")]
    embedder = MagicMock()
    requests = [
        {"op": "search", "queries": ["anything"], "top_k": 3},
        {
            "op": "chunks",
            "path": "src/a.py",
            "start_line": 1,
            "end_line": 1,
        },
    ]
    input_text: str = "\n".join(json.dumps(request) for request in requests)

    # Act
    with (
        patch(
            "smritikosh.exploration_cli.ReadOnlyExplorer",
            return_value=explorer,
        ) as explorer_factory,
        patch(
            "smritikosh.exploration_cli.make_embedder",
            return_value=embedder,
        ) as embedder_factory,
    ):
        result = CliRunner().invoke(
            main,
            ["explore", "batch", "--db-path", str(db_path)],
            input=input_text,
        )

    # Assert
    assert result.exit_code == 0
    explorer_factory.assert_called_once_with(str(db_path))
    embedder_factory.assert_called_once_with()
    output = toons.loads(result.output)
    assert [item["op"] for item in output] == ["search", "chunks"]
    assert output[0]["results"][0]["path"] == "src/a.py"
    assert output[1]["lines"] == [{"line_number": 1, "text": "def a():"}]


def test_should_return_outline_when_batch_chunks_has_no_range(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.get_outline.return_value = [
        OutlineEntry("load", "function", 3, 20),
    ]

    # Act
    with patch(
        "smritikosh.exploration_cli.ReadOnlyExplorer",
        return_value=explorer,
    ):
        result = CliRunner().invoke(
            main,
            ["explore", "batch", "--db-path", str(db_path)],
            input=json.dumps({"op": "chunks", "path": "src/a.py"}),
        )

    # Assert
    assert result.exit_code == 0
    explorer.get_outline.assert_called_once_with("src/a.py")
    explorer.get_source_lines.assert_not_called()
    assert toons.loads(result.output)[0]["outline"] == [
        {
            "symbol": "load",
            "chunk_kind": "function",
            "start_line": 3,
            "end_line": 20,
        }
    ]


def test_should_accept_batch_aliases_and_exact_text_operation(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.semantic_search.return_value = []
    explorer.find_text_lines.return_value = [
        TextMatch("src/a.py", 4, "TOTAL = 1", True)
    ]
    requests = [
        {"tool": "search", "query": "anything"},
        {"op": "text", "text": "TOTAL"},
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
            ["explore", "batch", "--db-path", str(db_path)],
            input="\n".join(json.dumps(request) for request in requests),
        )

    # Assert
    assert result.exit_code == 0
    output = toons.loads(result.output)
    assert [item["op"] for item in output] == ["search", "text"]
    assert output[1]["matches"][0]["line_number"] == 4


def test_should_accept_ignored_db_path_for_tools(tmp_path: Path) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()

    # Act
    result = CliRunner().invoke(
        main,
        ["explore", "tools", "--db-path", str(db_path)],
    )

    # Assert
    assert result.exit_code == 0
    assert toons.loads(result.output)["version"] == 5


def test_should_build_bounded_evidence_from_multiple_queries(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    shared = SearchResult(
        "src/a.py",
        3,
        4,
        "def publish():\n    pass",
        0.91,
        "function",
        "publish",
    )
    explorer.semantic_search.side_effect = [
        [shared],
        [
            shared,
            SearchResult(
                "tests/test_a.py",
                8,
                9,
                "def test_publish():\n    pass",
                0.85,
                "function",
                "test_publish",
            ),
        ],
    ]
    explorer.get_source_lines.side_effect = lambda path, **_: (
        [SourceLine(3, "def publish():"), SourceLine(4, "    pass")]
        if path == "src/a.py"
        else [SourceLine(8, "def test_publish():"), SourceLine(9, "    pass")]
    )
    embedder = MagicMock()
    lexical_store = MagicMock()
    lexical_store.search.return_value = []

    # Act
    with (
        patch(
            "smritikosh.exploration_cli.DuckDBSourceReader",
            return_value=explorer,
        ),
        patch(
            "smritikosh.exploration_cli.DuckDBBm25Store",
            return_value=lexical_store,
        ),
        patch(
            "smritikosh.exploration_cli.make_embedder",
            return_value=embedder,
        ) as embedder_factory,
    ):
        result = CliRunner().invoke(
            main,
            [
                "explore",
                "evidence",
                "publication flow",
                "publication tests",
                "--per-query",
                "2",
                "--max-chars",
                "2000",
                "--db-path",
                str(db_path),
            ],
        )

    # Assert
    assert result.exit_code == 0
    embedder_factory.assert_called_once_with()
    assert explorer.semantic_search.call_count == 2
    assert explorer.semantic_search.call_args_list[1].args[0] == ["publication tests"]
    payload = toons.loads(result.output)
    assert len(result.output) <= 2000
    assert len(payload["evidence"]) == 2
    assert payload["evidence"][0]["facets"] == [
        "publication flow",
        "publication tests",
    ]


def test_should_expand_evidence_window_to_complete_definition(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.semantic_search.return_value = [
        SearchResult(
            "src/helper.py",
            50,
            60,
            "except Exception:\n    raise",
            0.8,
            "function",
            "record_and_publish",
        )
    ]
    explorer.get_outline.return_value = [
        OutlineEntry("record_and_publish", "function", 10, 60)
    ]
    explorer.get_source_lines.return_value = [
        SourceLine(10, "def record_and_publish():"),
        SourceLine(60, "    raise"),
    ]
    lexical_store = MagicMock()
    lexical_store.search.return_value = []

    # Act
    with (
        patch(
            "smritikosh.exploration_cli.DuckDBSourceReader",
            return_value=explorer,
        ),
        patch(
            "smritikosh.exploration_cli.DuckDBBm25Store",
            return_value=lexical_store,
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
                "evidence",
                "publication retry",
                "--max-results",
                "1",
                "--db-path",
                str(db_path),
            ],
        )

    # Assert
    assert result.exit_code == 0
    evidence = toons.loads(result.output)["evidence"][0]
    assert (evidence["start_line"], evidence["end_line"]) == (10, 60)


def test_should_prefer_relevant_source_over_higher_scoring_documentation(
    tmp_path: Path,
) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    explorer = _mock_explorer()
    explorer.semantic_search.return_value = [
        SearchResult(
            "docs/retry.md",
            1,
            5,
            "# Generic retry guide",
            0.6,
            "section",
            "Retry guide",
        ),
        SearchResult(
            "clients/redis/client.py",
            40,
            50,
            "def decrement():\n    return redis.decr()",
            0.5,
            "method",
            "decrement",
        ),
    ]
    explorer.get_outline.side_effect = [
        [OutlineEntry("decrement", "method", 40, 50)],
        [OutlineEntry("decrement", "method", 40, 50)],
    ]
    explorer.get_source_lines.return_value = [
        SourceLine(40, "def decrement():"),
        SourceLine(50, "    return redis.decr()"),
    ]
    explorer.get_chunks_by_ids.return_value = [
        IndexedChunk(
            "redis",
            "clients/redis/client.py",
            40,
            50,
            "def decrement():\n    return redis.decr()",
            "method",
            "decrement",
        )
    ]
    lexical_store = MagicMock()
    lexical_store.search.return_value = [("redis", 1.0)]

    # Act
    with (
        patch(
            "smritikosh.exploration_cli.DuckDBSourceReader",
            return_value=explorer,
        ),
        patch(
            "smritikosh.exploration_cli.DuckDBBm25Store",
            return_value=lexical_store,
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
                "evidence",
                "redis decrement retry",
                "--per-query",
                "1",
                "--max-results",
                "1",
                "--db-path",
                str(db_path),
            ],
        )

    # Assert
    assert result.exit_code == 0
    evidence = toons.loads(result.output)["evidence"]
    assert [item["path"] for item in evidence] == ["clients/redis/client.py"]


def test_should_clamp_evidence_limits_instead_of_failing(tmp_path: Path) -> None:
    # Arrange
    db_path: Path = tmp_path / "index.duckdb"
    db_path.touch()
    service = MagicMock()
    service.retrieve.return_value = EvidencePack((), (), ("query",), False)

    # Act
    with (
        patch(
            "smritikosh.exploration_cli.DuckDBSourceReader",
            return_value=MagicMock(),
        ),
        patch(
            "smritikosh.exploration_cli.DuckDBBm25Store",
            return_value=MagicMock(),
        ),
        patch("smritikosh.exploration_cli.EvidenceService", return_value=service),
        patch("smritikosh.exploration_cli.make_embedder", return_value=MagicMock()),
    ):
        result = CliRunner().invoke(
            main,
            [
                "explore",
                "evidence",
                "query",
                "--per-query",
                "9",
                "--max-results",
                "48",
                "--max-source-lines",
                "500",
                "--max-chars",
                "60000",
                "--db-path",
                str(db_path),
            ],
        )

    # Assert
    assert result.exit_code == 0
    options = service.retrieve.call_args.kwargs["options"]
    assert (options.max_results, options.max_source_lines, options.max_chars) == (
        24,
        120,
        45_000,
    )
