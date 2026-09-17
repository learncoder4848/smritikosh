# Production-triage benchmark prompt

An account's billing cycle closed, but the customer received neither a PDF
statement nor a statement-ready notification.

Investigate the indexed portfolio and determine:

1. Which service owns each decision in the end-to-end flow, distinguishing
   decision owners from data providers and event consumers.
2. Every verified gate that can prevent cycle processing, statement/PDF
   generation, ready-event publication, or customer notification.
3. The exact trigger chain from cycle close through PDF render/upload and
   statement-ready notification.
4. Which tests prove both the suppressing and successful paths.

Use only the Smritikosh exploration CLI. Every executed command must begin with
`smritikosh explore`.

First run exactly:

```shell
smritikosh explore tools --toon
```

For every subsequent command, pass:

```shell
--db-path /Users/svashishtha/Documents/Github/smritikosh/multi_repo_smritikosh.duckdb
```

## Exploration strategy

- Follow the CLI's search → chunks → answer workflow.
- Search with 4–8 focused facets per call and use `--max-results 12` by
  default. Organize searches around:
  - cycle-close eligibility, scheduling, and initial event publication;
  - statement suppression flags and PDF generation/upload;
  - ready-event routing, notification gates, and preference handling;
  - tests for negative and positive paths;
  - upstream account and ledger inputs that influence these decisions.
- Search results are candidate locations, not evidence. Verify every material
  conclusion by reading source with `explore chunks`.
- Batch independent source reads into one command by repeating
  `--range PATH START END`. Use a file outline only when a returned range is
  too broad to inspect efficiently.
- Avoid rereading overlapping ranges. Prefer one complete definition plus its
  directly relevant tests.
- Target no more than 12 exploration calls after the initial `tools` call.
  Exceed this only when required to close an evidence gap listed below.

## Required evidence coverage

Before answering, verify or explicitly mark unverified:

- the owner of cycle eligibility and the first downstream event;
- the consumer of that event and the exact PDF/ready-event suppression
  predicate;
- PDF rendering, storage/upload, and ready-event publication;
- ready-event routing and all notification gates relevant to this statement;
- notification-preference lookup or filtering;
- account and ledger services' actual roles, if any;
- at least one test for the principal suppression path and one test for the
  successful PDF/event path;
- tests for eligibility, routing, and notification behavior where present.

Do not infer ownership merely because a service stores or supplies data. Do not
claim runtime root cause without account-specific logs, events, or database
state.

## Final answer

Return a concise report with these sections:

1. **Most likely explanation** — hypothesis and confidence, not a confirmed
   runtime cause.
2. **Ownership and trigger chain** — ordered end-to-end flow.
3. **Suppression matrix** — gate, owning service, effect, and evidence.
4. **Tests proving behavior** — test name, behavior proved, and evidence.
5. **Operational verification order** — minimum checks needed for the affected
   account.
6. **Unverified items** — source not read, missing test coverage, or runtime
   evidence unavailable.

Support every material code claim with exact portfolio-relative
`PATH:START-END` citations. Cite only ranges actually returned by
`explore chunks`; do not cite search-result locations as if they were read.

Do not use `grep`, `rg`, `find`, `ls`, `cat`, `sed`, `head`, `tail`, `Read`,
or `Glob`. Do not modify files, run tests, call external services, or perform
writes.
