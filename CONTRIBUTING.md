# Contributing

## Commits

Format: `type | short title`

Types: `feat` `fix` `docs` `refactor` `chore` `test`

- Imperative, lowercase title after the pipe
- One logical change per commit
- No filler body text; add a body only when the title is not enough

```
feat | add DuckDB storage adapter
fix | skip excluded JSON lockfiles in FileRouter
docs | add v1 indexing plan
```

## Attribution

Every commit is authored by the person accountable for the change.

- `Author`, `Committer`, and `Co-authored-by` name people only
- Never credit an assistant, bot, or tool: no `Co-authored-by: Cursor`,
  `Claude`, `Copilot`, or similar, and no "generated with" trailers
- Tools may help you write a change; they do not sign it
- Strip any trailer a tool adds before pushing:

  ```
  git commit --amend        # last commit
  git rebase -i main        # a range, then reword each
  ```

## Pull requests

- Title uses the same `type | title` format as the commit
- Body: 1–3 sentences on what changed and why
- One concern per PR
- Do not paste design essays, test-plan checklists, or generated-by notes
- Rebase onto `main` before merge; do not leave the PR based on a rewritten ancestor
