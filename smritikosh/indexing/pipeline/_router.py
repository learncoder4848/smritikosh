"""File routing configuration — maps extensions to languages and strategies.

Adding a new language is one register_extension() call here.
"""

from __future__ import annotations

import functools

from smritikosh.indexing.file_router import FileRouter, JsonExcludeFilter
from smritikosh.indexing.strategies import (
    AstChunkingStrategy,
    RegexChunkingStrategy,
    SectionChunkingStrategy,
)


@functools.cache
def _build_router() -> FileRouter:
    """Return a FileRouter pre-configured for all supported file types.

    Cached: strategies and router are constructed once per process and
    reused across every _run_pipeline call (e.g. in --watch mode).
    """
    ast      = AstChunkingStrategy()
    sections = SectionChunkingStrategy()
    toml     = RegexChunkingStrategy(r"^\[+[^\]]+\]")

    router = FileRouter(json_exclude_filter=JsonExcludeFilter())
    router.register_extension(".py",   "python",     ast)
    router.register_extension(".ts",   "typescript", ast)
    router.register_extension(".tsx",  "typescript", ast)
    router.register_extension(".js",   "javascript", ast)
    router.register_extension(".jsx",  "javascript", ast)
    router.register_extension(".java", "java",       ast)
    router.register_extension(".kt",   "kotlin",     ast)
    router.register_extension(".kts",  "kotlin",     ast)
    router.register_extension(".md",   "markdown",   sections)
    router.register_extension(".mdx",  "markdown",   sections)
    router.register_extension(".toml", "toml",       toml, has_tags_scm=False)
    router.register_extension(".json", "json",       sections)
    return router
