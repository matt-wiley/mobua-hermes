# Fix report: ticket 04 code-review minors

- **Covers:** follow-ups to `docs/specs/design-consistency-pass/report.md` (review of
  `13eabf9..61712d1`) on branch `feat/draft-promotion-and-ci`.
- **Spec:** `docs/specs/design-consistency-pass/spec.md`, ticket `design-consistency-pass-04`
- **Date:** 2026-10-17

## What was fixed
The review found no blockers or majors. This fix handles the minors that fit the fix lane:
test gaps, comments, two single-file readability changes and stale docs. None of these changes
alter behavior.

| Review finding | Change |
|---|---|
| Failed commit checked only after rollback (AC-65) | `test_a_failed_commit_leaves_...` asserts committed state before rollback too |
| Lock-wait race branch untested (item 1) | New threaded test `test_a_promotion_overlapping_an_uncommitted_sibling_promotion_waits_then_conflicts` |
| Save race not log-asserted (item 4) | Asserts the exact `plugin_draft.conflict` event (`reason=stale_version`) |
| API race not log-asserted (item 4) | Asserts stdout has `plugin_draft.conflict` and no `api.database_failed` |
| CLI lacks foreign-Revision selection and INSERT commit failure (AC-67, AC-69) | Two new parametrized CLI cases |
| Only `note`/`manifest` immutability tested (AC-68) | Parametrized over `code`, `parent_revision_id`, `created_by`, `created_at` |
| Claim comment doesn't say why not FOR UPDATE, isolation assumptions unstated | Comment in `drafts.py` states both |
| Clever `match` in `draft promote`, unexplained `get_draft` call | Plain `if`/`elif`/`else`, plus a why-comment |
| Pointer write inside a short-circuit test in `select_current_revision` | Explicit steps: move, then one conflict path |
| `evidence/04.md` races paragraph stale; "before rollback" overstated | Rewritten. Review follow-ups section added |
| Combined red summary for AC-65/66/81 | Per-criterion mutation reds recorded in `evidence/04.md` |
| Fix report red didn't explain the lock error | One sentence added to `fix-concurrent-promotion-number/report.md` |
| Ticket 04 implied a new migration | Wording corrected |
| AC-81 test-output clause untestable yet | Evidence notes that ticket 15 (AC-71) verifies it |

## Escalated, not fixed
These hit the fix lane's escalation triggers. Each needs a decision, or touches several files or
an interface. Route them through `/mobua-swe:grill` (or `/mobua-swe:refactor` for the last one).

1. **`plugin_draft.promoted` is logged before commit** (AC-69, "Success is reported only after
   commit"). Moving success events after commit touches the service and both surfaces, and also
   affects ticket 03's `plugin_draft.deleted`. The alternative is to record flush-time events in
   the spec or an ADR. Either way, it's a decision first.
2. **Unlisted events** `plugin_revision.selection_rejected` and `plugin.not_found`: amend the
   spec's Observability list, or fold them into listed events. This is a spec decision.
3. **UTC normalization only in `RevisionDetails`**: a shared `TypeDecorator` changes every
   `created_at` read across models.
4. **Pinning the isolation level** in `create_engine_for`: a config change. The assumption is now
   documented in the claim comment instead.
5. **`ImmutableRevisionError` signals a bulk update with an empty attribute list**: a public
   exception interface change.
6. **No researched standards for Typer 0.27, Pydantic 2.14 and Alembic 1.20**: run
   `/mobua-swe:setup` or the standards research.

## Criterion evidence
The criterion: each listed finding is resolved by a test that fails without the behavior it
pins, with all gates green.

Reds come from mutations, because the behavior was already correct. They were run in a scratch
worktree at `61712d1` with the new tests. Full table in `evidence/04.md`, "Review follow-ups".

- `drafts.py` from `8084970` (no claim): all 4 service race tests (including the new lock-wait
  test) and the API race test fail.
- `_conflict` logs nothing: the save race fails, along with the stale-version tests.
- `selection_conflict` logs nothing: the API race fails, along with the API stdout test.
- The guard ignores code, ancestry and metadata: all 4 new immutability cases fail.
- Selection ignores the target's Plugin and Reader: CLI `other_plugin` and `foreign_revision` fail.
- The CLI prints inside the transaction: both CLI promote commit-failure cases fail, including
  the new INSERT case.
- The failed-commit before-rollback assertion has no red: nothing can make a failed SQLite
  commit partly persist.

Green: the lock-wait test passed 25 of 25 repeated runs (about 0.55 s each).

## Gates
| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass (0 errors) |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass (166 files formatted; 1 contract kept) |
| Full suite | `uv run pytest` | pass (418 passed; 411 before, plus 7 new) |

No tests were deleted, skipped or weakened.

## Observability added
- No new log events. Existing failure-mode events are now asserted on paths that weren't
  checked before: the save race (`plugin_draft.conflict`, `stale_version`), and the API race
  (`plugin_draft.conflict` present, `api.database_failed` absent).

## Not verified
Code complete is not deployment verified. This fix did **not** verify:
- Deployment, or runtime behavior in a container.
- Postgres behavior of the claim's wait and re-read under READ COMMITTED (ticket 21).
- The escalated items above.

## Deployment verification checklist
- [ ] **Overlapping promotions:** send two concurrent `POST .../drafts/{d}/promote` requests for sibling Drafts.
  - One returns 201, and the other returns 409 `stale_current_selection`.
  - `docker logs` shows `plugin_draft.conflict` and no `api.database_failed`.
  - On Postgres, the second request waits briefly and then returns 409.
- [ ] **CLI promote options:** `news plugin draft promote` with both `--directory` and `--expected-version`, or with neither.
  - Exit 2 with "give exactly one of --directory or --expected-version".
  - With `--directory` and an unknown Draft id, the error names the Draft, not the workspace.
- [ ] **Selection:** `PUT .../current-revision` with a stale `expected_current_revision_id`.
  - 409 `stale_current_selection`, and `plugin_draft.conflict` with `operation=select_current`.
  - With a correct one: 200, and the pointer moves.
