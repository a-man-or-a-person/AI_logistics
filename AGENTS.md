## Agent skills

### Issue tracker

Issues and specs are tracked as local Markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Domain docs

This repository uses a single-context domain documentation layout. See `docs/agents/domain.md`.

## Development workflow

For development, review, PR delivery or release acceptance, follow [Agent Workflow v2](docs/agents/development-workflow.md).

- Before edits, verify repository/worktree path, remote, branch and base HEAD; read the owned contract, classify risk, name one accountable implementer and list affected callers, tests, fixtures, config, exports and CURRENT docs.
- Work on an isolated branch. Reproduce defects with genuine RED → GREEN; preserve working increments. For UI/API changes, run early live smoke and the applicable cache, stale, cancellation, retry and focus transitions. Use independent oracles for business metrics.
- Before merge, complete risk-based review and all existing mandatory gates on final HEAD, with zero skipped mandatory tests. Verify the running checkout, port and served assets when handing off an application. Report functional, human and production readiness separately.

Task-specific approved obligations and required repository checks remain binding. Merge and cleanup require the user's authorization; preserve unrelated work and private data.
