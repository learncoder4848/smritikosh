# Contributing

## Commits

Format: `type | short title`

Types: `feat` `fix` `docs` `refactor` `chore` `test`

- Imperative, lowercase title after the pipe
- One logical change per commit
- Author and `Co-authored-by` must be people only
- No filler body text; add a body only when the title is not enough

```
feat | add DuckDB storage adapter
fix | skip excluded JSON lockfiles in FileRouter
docs | add v1 indexing plan
```

## Pull requests

- Title uses the same `type | title` format as the commit
- Body: 1–3 sentences on what changed and why
- One concern per PR
- Do not paste design essays, test-plan checklists, or generated-by notes
- Rebase onto `main` before merge; do not leave the PR based on a rewritten ancestor
