"""Tests for file routing and the JSON exclude filter."""

from __future__ import annotations

import pytest

from smritikosh.indexing.file_router import FileRouter, JsonExcludeFilter, RouteConfig
from tests.indexing.conftest import FakeStrategy

STRATEGY = FakeStrategy()


@pytest.fixture
def router() -> FileRouter:
    router = FileRouter()
    router.register_extension(".py", "python", STRATEGY)
    router.register_extension(".json", "json", STRATEGY)
    router.register_extension(".toml", "toml", STRATEGY, has_tags_scm=False)
    return router


# ── JsonExcludeFilter ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("path", "excluded"),
    [
        ("package-lock.json", True),  # exact filename
        ("deps/foo-lock.json", True),  # *-lock.json
        ("assets/bundle.min.json", True),  # *.min.json
        ("assets/app.chunk.json", True),  # *.chunk.json
        ("src/__fixtures__/response.json", True),  # excluded dir segment
        ("web/.next/build-manifest.json", True),
        ("config/eval_config.json", False),  # user config
        ("tsconfig.json", False),
        ("src/data/fixtures", False),  # dir name, but it is the file
    ],
)
def test_should_exclude_only_machine_generated_json(path: str, excluded: bool) -> None:
    assert JsonExcludeFilter().is_excluded(path) is excluded


@pytest.mark.parametrize(
    ("kwargs", "path"),
    [
        ({"extra_filenames": {"local.json"}}, "local.json"),
        ({"extra_patterns": ("*.snap.json",)}, "ui/button.snap.json"),
        ({"extra_dirs": {"vendor"}}, "vendor/config.json"),
    ],
)
def test_should_exclude_extras_without_dropping_defaults(
    kwargs: dict[str, object], path: str
) -> None:
    custom = JsonExcludeFilter(**kwargs)  # type: ignore[arg-type]

    assert custom.is_excluded(path) is True
    assert custom.is_excluded("package-lock.json") is True


# ── FileRouter ────────────────────────────────────────────────────────────────


def test_should_return_none_when_json_is_excluded(router: FileRouter) -> None:
    assert router.route("package-lock.json") is None
    assert router.route("src/__fixtures__/response.json") is None


def test_should_return_config_when_json_is_user_config(router: FileRouter) -> None:
    assert router.route("config/eval_config.json") == RouteConfig(
        language="json", strategy=STRATEGY, has_tags_scm=True
    )


def test_should_prefer_filename_route_over_extension_route(
    router: FileRouter,
) -> None:
    override = FakeStrategy()
    router.register_filename("setup.py", "setup", override)

    route = router.route("tools/setup.py")

    assert route == RouteConfig("setup", override, True)


def test_should_match_extension_when_case_differs() -> None:
    router = FileRouter()
    router.register_extension(".PY", "python", STRATEGY)

    assert router.route("a.py") is not None
    assert router.route("B.Py") is not None


def test_should_return_none_when_extension_not_registered(router: FileRouter) -> None:
    assert router.route("assets/logo.png") is None
    assert router.route("Makefile") is None


def test_should_ignore_json_filter_for_other_extensions(router: FileRouter) -> None:
    """__fixtures__ excludes JSON only -- a .py living there is still code."""
    route = router.route("tests/__fixtures__/helper.py")

    assert route == RouteConfig("python", STRATEGY, True)


def test_should_carry_has_tags_scm_false_for_toml(router: FileRouter) -> None:
    route = router.route("pyproject.toml")

    assert route is not None
    assert route.has_tags_scm is False
