# Code-complete report: Design consistency pass (ticket 04)

- **Covers:** `13eabf9..61712d1` on branch `feat/draft-promotion-and-ci` (PR group 2). The
  branch merge-base with `main` is `13eabf913e452161141fdfa42407c8b94dcf61f1`. Code commits:
  `03b642c`, `fac30cc`, `0934996`, `e0122be`, `5dd2880`, `61712d1`. Records: `8084970`
  (evidence), `c2978e5` (the previous report). Ticket 21, the other member of group 2, has not
  started and is not reviewed here.
- **Spec:** `docs/specs/design-consistency-pass/spec.md`
- **Tickets:** `design-consistency-pass-04` (local status `done`), covering AC-49, AC-65,
  AC-66, AC-67, AC-68, AC-69, AC-81. Evidence: `evidence/04.md`, plus
  `docs/specs/fix-concurrent-promotion-number/report.md` for `61712d1`.
- **Sync:** n/a, because the ticket has `external: null`.
- **Date:** 2026-10-17. This report replaces the review of `13eabf9..8084970`.

## Verdict
**CODE COMPLETE**: all three axes pass and every code-complete item holds. The earlier major
(concurrent same-number promotion untested) is fixed by `61712d1`. That fix is covered by
real-connection race tests at the service and API layers, and they fail against the old code.
Only minor findings remain.

## Findings
There are no blockers or majors. Each finding cites its source.

### Standards (PASS)
- [minor] `src/news/service/drafts.py:278-292`
  - Rule: baseline §1, "comments say **why**", and §5, "Every failure mode is either handled deliberately or fails loudly".
  - Problem: the Plugin-row claim is a no-op conditional `UPDATE` in place of `with_for_update()`, and the comment does not say why (SQLite ignores row locks).
  - Problem: correctness also depends on two assumptions that nothing pins: READ COMMITTED on Postgres, and pysqlite's legacy implicit BEGIN on SQLite. Under REPEATABLE READ, or with an explicit-BEGIN SQLite recipe, the losing race becomes a 503 instead of a 409.
  - Problem: the claim repeats `revision_history.move_current_pointer`'s compare-and-set (`revision_history.py:108-120`).
  - Fix: state both assumptions in the comment, or pin `isolation_level` in `create_engine_for`. Optionally share the compare-and-set helper.
- [minor] `src/news/cli/main.py:344-351`
  - Rule: baseline §1, "Prefer plain, obvious constructs over clever ones".
  - Problem: the tuple `match` binds `version` in a `pass` arm. The discarded `get_draft(...)` call has no comment saying it reports DraftNotFound before the workspace is read. This finding is still open from the last review.
  - Fix: use a plain exactly-one-of `if`, and add a why-comment on the existence check.
- [minor] `src/news/service/revision_history.py:95`
  - Rule: baseline §1, "Prefer plain, obvious constructs over clever ones".
  - Problem: `if problem is None and move_current_pointer(...)` runs a write inside a short-circuit test. The fall-through then rebuilds the reason with `problem or "stale_current_selection"`.
  - Fix: split it into explicit steps: a problem conflict, then a failed-pointer-move conflict, then flush.
- [minor] `src/news/service/models.py:207-254`
  - Rule: baseline §1, "Names carry the meaning".
  - Problem: `ImmutableRevisionError(table, [])` uses an empty attribute list to signal a bulk update.
  - Fix: add an explicit `operation: Literal["update", "bulk_update", "delete"]`, or named constructors.
- [minor] `src/news/service/plugin_data.py`, the UTC projection. This is still open from the last review.
  - Rule: baseline §4.
  - Problem: SQLite's naive `created_at` is normalized only in the `RevisionDetails` projection.
  - Fix: use a shared `TypeDecorator`, or record why the projection is the boundary.
- Snapshot freshness: current. `docs/standards.md` matches Python 3.14, FastAPI 0.143 and SQLAlchemy 2.1. There is a gap but no staleness: Typer 0.27, Pydantic 2.14 and Alembic 1.20 have no researched rules.

### Spec (PASS)
- [minor] `src/news/service/drafts.py:324`
  - Source: AC-69, "Success is reported only after commit".
  - Problem: `plugin_draft.promoted` is logged at flush, before the surface commits. A failed commit still leaves a "promoted" line in the log. The commit-failure tests don't assert on logs.
  - Fix: log after commit, or record flush-time events in the spec or an ADR. Either way, assert logs in the commit-failure tests.
- [minor] `src/news/service/revision_history.py:87,157`
  - Source: the spec Observability list names only `plugin_draft.*` for this flow.
  - Problem: `plugin_revision.selection_rejected` and `plugin.not_found` are not in the spec.
  - Fix: amend the Observability list, or fold these into listed events.
- [minor] `tests/service/test_promotion.py:257-268`
  - Source: AC-65, "Check state before rollback and committed state".
  - Problem: the failed-commit test checks committed state only after `session.rollback()`. Line 73 of `evidence/04.md` overstates this.
  - Fix: assert `committed_state(engine) == before` before the rollback.
- [minor] `tests/service/test_immutability.py`
  - Source: AC-68, "Manifest/code/ancestry/metadata remain immutable".
  - Problem: only `note` and `manifest` updates are tested.
  - Fix: parametrize over `code`, `parent_revision_id`, `created_by` and `created_at`.
- [minor] `tests/cli/test_revisions.py`
  - Source: AC-67.
  - Problem: the CLI lacks two cases the API tests have: a foreign Revision inside one's own Plugin, and a `plugin_revision` INSERT commit failure.
  - Fix: add the two parametrized cases.
- [minor] AC-81, "test stdout/stderr are returned only to the invoking caller"
  - Problem: this clause can't be tested until Test Runs exist.
  - Fix: note in the tickets README or the evidence that the Test Run tickets (AC-71/75) verify it.
- Note: ticket 04 line 43 mentions "a new migration", but none was needed. The ticket 03 schema plus the ORM guard satisfy AC-68 ("service/ORM"). Correct the ticket wording.
- Scope: nothing beyond the ticket. Nothing contradicts ADR 0024 or D-25/ADR 0022.

### Code-complete evidence (PASS)
- [minor] `src/news/service/drafts.py:278-292`, `tests/service/test_promotion.py`
  - Source: item 1, each failure mode.
  - Problem: the claim's lock-wait branch has no committed test. In that branch a competitor is mid-transaction and the claim waits on its write lock. Every committed race test interleaves before the claim. The reviewer ran a threaded scratch probe: the promotion waited about 1.1 s, then raised `stale_current_selection`, and the numbers were `[1, 2]`. The behavior holds on SQLite, but the suite doesn't pin it.
  - Fix: add a threaded test that pauses the competitor after its `UPDATE plugin` (`after_cursor_execute` plus `threading.Event`).
- [minor] `evidence/04.md:80-86`
  - Source: evidence accuracy.
  - Problem: this text is stale after `61712d1`. It still says the hook commits "just before the Revision INSERT. Two cases". There are now three race cases, all interleaved before `UPDATE plugin`.
  - Fix: update the Races paragraph.
- [minor] `docs/specs/fix-concurrent-promotion-number/report.md`, the "Red" section
  - Source: item 2, red for the right reason.
  - Problem: the recorded service red is `IntegrityError UNIQUE`, from the old interleave point. Against the old code, the committed test now fails with `database is locked`. Both show the defect, but the report doesn't say so.
  - Fix: add one sentence noting the difference.
- [minor] `tests/service/test_promotion.py`, `test_a_save_racing_the_promotion_is_a_conflict_after_rollback`
  - Source: item 4.
  - Problem: no `capture_logs()`. The pointer and sibling races now assert `plugin_draft.conflict`, but this one doesn't.
  - Fix: assert the event (`operation="promote"`, the versions and the reason).
- [minor] `tests/api/test_revisions.py:157-180`
  - Source: item 4.
  - Problem: the API race test doesn't check that stdout has `plugin_draft.conflict` and no `api.database_failed`. Those log lines are the observable difference the fix promises.
  - Fix: parse stdout the way the lifecycle-log test does.
- [minor] `evidence/04.md`, the AC-65, AC-66 and AC-81 sections
  - Source: item 2.
  - Problem: these sections still rely on one combined red summary. This finding is still open from the last review.
  - Fix: add a red excerpt per criterion.
- Resolved since the last review:
  - The concurrent same-number major. The reviewer restored the pre-fix `drafts.py` in a scratch copy, and all 4 race tests failed. The API test got 503 instead of 409.
  - The race-conflict logging minor, for the pointer and sibling races.

## Criteria evidence
| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| AC-49 | `test_implementation`: exact pin accepted; `>=`, `~=`, `==6.*`, ranges, URL and bare name rejected; no-deps accepted; malformed metadata rejected. Promotion, API and CLI invalid-Draft tests | yes | yes | yes (empty, no block, `[]`, CRLF) | yes (`===`, `==6.*`) | yes | yes |
| AC-65 | `test_promotion`: creates current Revision, flushed-not-committed, invalid Draft, stale or future version, failed commit, save/pointer/sibling races. API and CLI commit-failure tests | yes | yes (failed commit not checked before rollback) | yes | yes (3 races) | combined summary | yes |
| AC-66 | sibling distinct numbers, `test_a_sibling_promotion_racing_for_the_same_number_is_a_conflict_after_rollback`, older parent needs confirmation (copied as-is), reconfirmation, numbering after pointer rollback. API sibling-race and confirmation tests | yes | yes (lock-wait branch probed only) | yes | yes | combined summary + fix report reds | yes |
| AC-67 | `test_revision_history`: tree, select older or current creates nothing, unknown/other-Plugin/foreign/Built-in rejected, Reader scope. API and CLI select/reject tests, CLI and API history parity | yes | yes (CLI foreign-Revision case missing) | yes | yes (Built-in) | yes | yes |
| AC-68 | `test_immutability`: delete rejected, bulk ORM statements guarded, update tests. No archive/delete in API or CLI. Channel Revision and Binding deletes allowed | yes | partial (code, ancestry, metadata updates) | n/a: no ranges | yes (bulk ORM bypass) | yes | yes |
| AC-69 | API and CLI commit failure (503, empty stdout), 409 and 422 bodies, CLI stderr, `test_promotion_does_not_require_a_successful_test_run` | yes | yes | n/a: no ranges | yes | yes | yes |
| AC-81 | Exact event dicts in service tests, API stdout lifecycle-log test, CLI log-file test, sentinel and requirement text absent | yes | yes (save race and API race not log-asserted) | n/a | yes (no leak to stdout) | not shown on its own | yes |

## Gates
Run independently by the reviewers on `61712d1`.

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass (0 errors, 0 warnings) |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass (166 files formatted; 1 contract kept, 0 broken) |
| Full suite | `uv run pytest` | pass (411 passed, 0 skipped, 0 failed) |
| Build | `uv build` | pass (sdist and wheel) |

No tests were deleted, skipped or weakened. `test_deleting_revision_rows_is_not_blocked` was
renamed with an identical body, and the route-inventory test was tightened. The new tests use
no mocks. Races and commit failures run on real migrated SQLite, through a second engine
connection and deferred-constraint triggers. Tests landed with their code in every code commit.

## Observability delivered
- Logs, all at info level through structlog. They carry ids, reason codes and field names only, with no Manifest, code, config or credentials:
  - `plugin_draft.promoted` (`drafts.py:324`)
  - `plugin_draft.rejected`
  - `plugin_draft.conflict` (now also emitted for a lost sibling-promotion race)
  - two events outside the spec, `plugin_revision.selection_rejected` and `plugin.not_found` (see Spec findings)
- Where the logs go: the CLI writes to its log file and the API to stdout, and tests cover both.
- Metrics: none, because the ticket says "No new metrics".

## Not verified
Code complete is not deployment verified. This review did **not** verify:
- Deployment, runtime behavior in the target environment, or real traffic and data.
- Postgres behavior of the claim's row lock, the `IS NOT DISTINCT FROM` and `RETURNING` conditional writes, and the bulk-ORM guard. Only SQLite was run; ticket 21 owns this.
- The lock-wait race branch in the committed suite. It was shown only by a scratch probe on SQLite.
- A CLI-level concurrent-promotion race. The CLI shares the service path.
- Spec deployment checks 10 and 11, which were never run in a container.

## Deployment verification checklist
Evaluate manually or in the observability system to confirm the deployed change matches the intent of the spec or ticket.

- [ ] **Invalid Draft (spec check 10).** Through the CLI and the API, save a Draft whose PEP 723 block has `feedparser>=6`, then promote it.
  - The save succeeds. Promotion returns 422 from the API (exit 1 from the CLI) with a field error under `code[main.py].dependencies`.
  - Draft, Revision count and current pointer are unchanged.
  - `plugin_draft.rejected` (`reason=invalid_implementation`, field codes only) appears in `docker logs` or the CLI log file, with no `feedparser` or source text.
- [ ] **Corrected promotion (spec check 10).** Pin `feedparser==6.0.11`, save and promote.
  - The API returns 201 (CLI exit 0). The new Revision is numbered max+1 and is current.
  - Only that Draft is gone, and Bindings stay on their pinned Revisions.
  - `plugin_draft.promoted` shows the Reader, Plugin, Draft, parent and Revision ids.
- [ ] **Stale workspace (spec check 11).** Export a Draft, update it through the API, then run `draft promote --directory` on the stale workspace.
  - The command returns a conflict naming both versions, with nothing on stdout, and no content is overwritten.
  - `plugin_draft.conflict` is logged with `operation=promote`.
- [ ] **Older-parent confirmation.** Select an older Revision, then promote a Draft whose parent is not current.
  - Without `--confirm-current` (`expected_current_revision_id`), the result is a 409 `confirmation_required`.
  - With it, the promotion succeeds and the code is copied as-is.
  - With a stale confirmation, the result is a 409 `stale_current_selection`.
- [ ] **Overlapping promotions (the `61712d1` fix).** Send two concurrent POSTs to `/readers/{r}/plugins/{p}/drafts/{d}/promote` for sibling Drafts.
  - One returns 201, and the other returns 409 `stale_current_selection` with `actual_current_revision_id` set to the winner.
  - `GET .../revisions` shows distinct numbers, and the losing Draft still exists.
  - The logs have `plugin_draft.conflict` and **no** `api.database_failed` for that request.
  - Repeat on Postgres (ticket 21). The second request should wait briefly and then return 409, with no deadlock and no 503.
- [ ] **History and selection (spec check 11).** Compare `news plugin revision list` with the `GET .../revisions` body.
  - They match.
  - Selecting an older Revision creates no Revision and leaves Bindings unchanged.
  - Selecting another Plugin's Revision or a foreign one returns 422 on `revision_id` with no change.
- [ ] **No deletion surface.** `/openapi.json` has no delete or archive route for Plugin Revisions, and `news plugin revision --help` lists no delete command.
