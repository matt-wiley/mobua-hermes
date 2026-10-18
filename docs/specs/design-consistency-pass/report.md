# Ticket 21 status: Postgres repository checks and core CI

- **Ticket:** [design-consistency-pass-21](tickets/21-postgres-and-core-ci.md).
- **Spec:** [AC-58 and AC-59](spec.md); AC-55 and AC-56 were withdrawn on 2026-10-18.
- **Tracking:** local ticket files only; no GitHub issues.
- **Branch:** `feat/docs-postgres-ci`.
- **Date:** 2026-10-18.

## Status

The user canceled automated ADR checking and requested removal of its implementation,
tests, CI job, parser dependency declaration, and repair/review artifacts. The prior
ADR parser findings are closed by scope cancellation, not by a parser repair. The
Postgres portability work, READ COMMITTED pin, promotion-race coverage, and four
application CI jobs remain in scope.

See [the removal report](../fix-remove-adr-checking/report.md) for the exact changes,
test-first evidence, and current validation. Historical Postgres and accepted AC-59
ordering-exception evidence remains in [evidence/21.md](evidence/21.md).
Independent review of the amended ticket is pending; this status update does not
claim a new CODE COMPLETE verdict.

## Not verified

Hosted PR/main CI execution and target-environment behavior remain unverified.

## Deployment verification checklist

- [ ] On a PR and a push to `main`, confirm all four application CI jobs run and pass.
- [ ] Confirm the pinned Postgres service becomes healthy and repository/schema tests pass.
- [ ] In the target Postgres environment, overlap sibling promotions: one succeeds and the other waits, then returns 409 `stale_current_selection`, with no deadlock or 503.
