# Fix report: concurrent promotions racing for a Revision number

- **Covers:** the fix commit after `8084970` on branch `feat/draft-promotion-and-ci`.
- **Source:** major Code-complete finding in `docs/specs/design-consistency-pass/report.md`
  (ticket `design-consistency-pass-04`, AC-66). The finding was an untested failure mode.
  Reproducing it showed that the behavior was wrong too.
- **Date:** 2026-10-17.

## Reproduction (criterion)

- **Expected:** the ticket's Seams section says "Concurrent pointer changes require fresh
  confirmation; do not merge". AC-69 asks for actionable conflict errors. So when two
  promotions of the same Plugin overlap, one should commit and the other should get a 409
  `stale_current_selection` conflict that names the new current Revision. Both should log
  `plugin_draft.conflict`, and the numbers must stay distinct (AC-66).
- **Actual:**
  1. The losing promotion read the same `max(number)` and computed the same number.
  2. Its `INSERT` then failed on the `(plugin_id, number)` unique constraint with a raw
     `IntegrityError`.
  3. The API answered 503 "Database operation failed; try again" and logged only
     `api.database_failed`. The CLI reported an unexpected error.
  4. No conflict event was logged.
- **Root cause:** `promote_draft` allocated the number and inserted the Revision before its
  conditional pointer write. The unique constraint therefore caught the race before the
  pointer check could classify it as a stale selection.
- **Fix:** `promote_draft` now claims the Plugin row with a conditional no-op `UPDATE`
  (`current_revision_id IS NOT DISTINCT FROM` the observed value) before reading
  `max(number)`. A competing promotion is in one of two states:
  - it has already moved the pointer, so the claim matches no row and raises
    `stale_current_selection`;
  - it is still running, so it waits on the row lock (Postgres) or the database write lock
    (SQLite), then re-evaluates and conflicts.

  Numbering therefore happens only while this transaction holds the claim. The later
  pointer move no longer needs to be conditional, and the dead conflict branch after the
  `INSERT` was removed. The change touches only `src/news/service/drafts.py`. No schema,
  interface or dependency changed.

## Evidence

| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| The loser of a concurrent promotion gets a stale-selection conflict, distinct numbers survive, nothing else changes | `tests/service/test_promotion.py::test_a_sibling_promotion_racing_for_the_same_number_is_a_conflict_after_rollback`, which checks the exception, the exact `plugin_draft.conflict` event, and the committed pointer, Draft and numbers `[1, 2]` after rollback; `tests/api/test_revisions.py::test_api_promotion_losing_a_race_for_the_number_is_an_actionable_conflict`, which checks the 409 body and history | n/a: failure path only; existing promotion tests cover success | yes: sibling promotion committed on a second connection | yes: the pointer-only race (`test_a_pointer_change_racing_the_promotion_is_a_conflict_after_rollback`, now also asserting its conflict event) | yes: a save racing the promotion still conflicts on the Draft version (`test_a_save_racing_the_promotion_is_a_conflict_after_rollback`) | yes | yes |

The three race tests now interleave the competing write just before promotion's first write
(`UPDATE plugin SET`) instead of before `INSERT INTO plugin_revision`. The claim made the
pointer write come first, and the old interleave point would make the second connection
wait on SQLite's write lock. Each test still asserts the same outcome.

**Red, service test, before the fix:**

```
E       sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError) UNIQUE constraint failed: plugin_revision.plugin_id, plugin_revision.number
FAILED tests/service/test_promotion.py::test_a_sibling_promotion_racing_for_the_same_number_is_a_conflict_after_rollback
1 failed, 17 deselected
```

**Red, API test, with `drafts.py` reverted:**

```
E       AssertionError: {"detail":"Database operation failed; try again."}
E       assert 503 == 409
{"error_type": "OperationalError", "event": "api.database_failed", "level": "error", ...}
```

At that interleave point the old code already held SQLite's write lock, so the competitor
hit a locked database rather than the unique constraint. The observable bug is the same: a
503 instead of an actionable 409.

**Green:** 18 passed in `tests/service/test_promotion.py`, and the API test passes.

## Gates

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass: 165 files formatted, 1 contract kept |
| Full suite | `uv run pytest` | pass: 411 tests |

## Observability added

- The lost race now emits the existing `info plugin_draft.conflict` event, with
  `operation="promote"`, `reason="stale_current_selection"` and the expected and actual
  current Revision ids. It used to emit only a generic `api.database_failed` error.
- No new events or metrics.

## Not verified

- Postgres row-lock behavior of the claim under real concurrent transactions (ticket 21
  owns Postgres checks). Only SQLite was exercised.
- A CLI-level race test. The CLI calls the same `promote_draft`, and `CurrentSelectionConflict`
  is already an expected CLI failure.
- Deployment.

## Deployment verification checklist

- [ ] **Overlapping promotions.** Create two sibling Drafts from the same parent of one
  Reader Plugin, then promote both at the same time (two API clients, or the CLI and the
  API). Check four things:
  - one promotion returns 201 and the other returns 409 `stale_current_selection`, naming
    the winner's Revision id;
  - the history shows distinct numbers;
  - the losing Draft still exists;
  - server stdout or the CLI log has `plugin_draft.conflict` with
    `reason="stale_current_selection"`, and there is no `api.database_failed` for that
    request.
- [ ] **Postgres.** Repeat the check above on Postgres. The second promotion should wait
  briefly on the row lock and then conflict, not deadlock or fail with 503.
