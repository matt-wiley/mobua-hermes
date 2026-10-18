# Removal report: canceled ADR checking

- **Base:** `cc604dee698e7c62f7b77cdcebd17005b993052f` on `feat/docs-postgres-ci`.
- **Ticket:** [design-consistency-pass-21](../design-consistency-pass/tickets/21-postgres-and-core-ci.md), tracked locally only.
- **Spec:** [design-consistency-pass](../design-consistency-pass/spec.md); AC-55/56 withdrawn and AC-59 amended.
- **Date:** 2026-10-18.

## Status

Removal implemented; local gates pass. Independent review of the amended scope remains
separate. The prior parser findings are closed by cancellation, not by a parser repair.

## Expected behavior and root cause

Expected: automated ADR validation no longer runs locally or in CI, and the spec and
contribution guidance impose no automation requirement. Actual before this change:
the checker, 85 checker cases, parser dependency declaration, CI job, and repair/review
documents still existed after the user canceled the work. The root cause was that
cancellation had stopped activity without removing its implementation and requirements.

The user's explicit removal request authorizes deleting checker-specific tests and
changing the CI/config/spec scope. No new application behavior, dependency, or migration
is introduced. Manual ADR documentation and the index remain maintained by hand.

## Changes

- Removed the checker and its test package, the dedicated parser dependency declaration,
  obsolete typecheck path, docs CI job, and the three dedicated parser repair document sets.
- Replaced the docs-job contract with a contract for exactly the four remaining
  application CI jobs; the other workflow assertions remain intact.
- Withdrew AC-55/56 without renumbering later criteria, amended AC-59, renamed ticket 21,
  and updated scope, coverage, deployment ownership, evidence, and contribution guidance.
- Recorded local-only ticket tracking in AGENTS.md, CONTRIBUTING.md, and the workflow
  configuration. No GitHub issue was created.
- Preserved Postgres fixtures, READ COMMITTED, promotion-race coverage, and application
  CI gates. No application source or retained service/database tests changed.

`markdown-it-py` remains in the lockfile as a transitive requirement of Rich; its
checker-specific direct requirement and version constraint are removed. No locked
package versions changed.

## Red and green evidence

Before changing the workflow, replaced its canceled-job test with
`test_core_ci_runs_only_the_required_application_gates`.

```text
$ uv run pytest tests/test_ci_workflow.py --tb=short
FAILED test_core_ci_runs_only_the_required_application_gates
E Extra items in the left set:
E 'docs'
1 failed, 5 passed in 0.07s
```

This is a scope/behavior failure, not a syntax or import error. After removing the job:

```text
$ uv run pytest tests/test_ci_workflow.py --tb=short
6 passed in 0.05s

$ uv run pytest
426 passed in 11.33s
```

The suite reduction from 511 to 426 is exactly the 85 deliberately removed checker
cases. The six workflow contracts still verify triggers, required gate commands, the
pinned Postgres service, full-SHA Actions, job scope, and failure propagation. No mocks,
skips, or xfails were introduced. Numeric limits and new application failure modes do
not apply to this feature removal.

## Gates

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors, warnings, informations |
| Lint | `uv run ruff check .` | pass |
| Formatting | `uv run ruff format --check .` | pass: 172 files already formatted |
| Import boundaries | `uv run lint-imports` | pass: 1 kept, 0 broken |
| Full SQLite suite | `uv run pytest` | pass: 426 tests |
| Workflow contracts | `uv run pytest tests/test_ci_workflow.py --tb=short` | pass: 6 tests |
| Lock consistency | `uv lock --check --offline` | pass: 53 packages resolved |
| Workflow syntax | pinned `rhysd/actionlint:1.7.12` against `.github/workflows/core.yml` | pass: exit 0, no diagnostics |
| Diff whitespace | `git diff --check` | pass |

## Observability

No new events or metrics are appropriate for removal of repository tooling. Application
CI jobs keep their existing names and failure propagation. The canceled checker was not run.

## Not verified

Code completion is not deployment verification. Hosted PR/main workflow execution and
target-environment behavior remain unverified. Postgres was not rerun for this removal;
the preceding ticket review passed 283 repository/schema tests, and its application
source, fixtures, and pinned service are unchanged. Independent review of this removal
may be requested with `/mobua-swe:code-review`; it is not an assessment of ADR contents.

## Deployment verification checklist

- [ ] In the next hosted PR/main run, confirm only typecheck, lint, SQLite, and Postgres jobs run and pass.
- [ ] Confirm the pinned Postgres service becomes healthy and its repository/schema command passes.
