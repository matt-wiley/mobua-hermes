# 0014. Own database-driven scheduler with per-Channel leases

Status: Accepted
Date: 2026-10-16

## Context

Channels run Collection and Publishing cadences (ADR 0002), must Catch-up after missed runs, survive restarts, and later share work across multiple workers (ADR 0006).

## Decision

Build a small scheduler in the service layer. It only carries out each Channel's own cadences; it never sets a rhythm. Each Channel stores a next-run-at time per cadence in the database; one async loop polls every few seconds and starts what's due. Overdue runs execute once and set the next time from now (Catch-up, i.e. coalescing). Late runs are never skipped. When both of a Channel's cadences are due, the Collection runs first and the Publish starts after it finishes. While a run is in progress the Channel holds a Run Lease; a run that comes due meanwhile stays due (its next-run-at is not advanced) and starts on the first poll after the lease is released. Leases expire after a timeout so a crash can't wedge a Channel. Postgres row locking later lets multiple workers share the loop.

Scope: widened 2026-10-16 (design consistency pass). The same scheduler also runs the Core agent's cadence, with the same lease and Catch-up behavior, so there is one scheduling mechanism.

## Alternatives rejected

- **APScheduler.** Built-in coalescing, misfire handling, and overlap limits, but another library and job store to understand, for behavior we can express in a few lines. Its overlap limits are also in-memory and don't survive crashes.

## Consequences

- Scheduling state lives entirely in the database and survives restarts.
- Lease timeouts must exceed the longest legitimate run.
- Polling interval bounds schedule precision (seconds, which is fine for news).
