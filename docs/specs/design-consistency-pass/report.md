# Code-complete report: Design consistency pass (ticket 04)

- **Covers:** `13eabf9..8084970` on branch `feat/draft-promotion-and-ci` (PR group 2). The
  branch merge-base with `main` is `13eabf913e452161141fdfa42407c8b94dcf61f1`. Commits:
  `03b642c`, `fac30cc`, `0934996`, `e0122be`, `5dd2880`, `8084970`. Ticket 21, the other
  member of group 2, has not started and is not reviewed here.
- **Spec:** `docs/specs/design-consistency-pass/spec.md`
- **Tickets:** `design-consistency-pass-04` (local status `done`), covering AC-49, AC-65,
  AC-66, AC-67, AC-68, AC-69, AC-81. Evidence: `evidence/04.md`.
- **Sync:** n/a, because the ticket has `external: null`.
- **Date:** 2026-10-17. This report replaces the ticket-03 report.

## Verdict
**NOT CODE COMPLETE**: one AC-66 failure mode has no test and no justification. Concurrent
promotions can pick the same Revision number, and nothing tests that case. All gates are
green, and the Standards and Spec axes pass with minor findings only.

## Findings
Blockers first. Each finding cites its source.

### Standards (PASS)
- [minor] `src/news/cli/main.py:344-351`
  - Rule: baseline §1 "Readability is king": "Prefer plain, obvious constructs over clever ones" and "comments say **why**".
  - Problem: the `match directory, expected_version:` block binds `version` in a `case None, int() as version: pass` arm and then uses it after the match. The discarded `get_draft(...)` call has no comment explaining that it reports DraftNotFound before the workspace marker is read.
  - Fix: use a plain `if`/`elif` that assigns `version`, and add a one-line comment on the existence check.
- [minor] `src/news/service/plugin_data.py:9-15,44`
  - Rule: baseline §4 "Do not write custom code or workarounds where an idiom exists".
  - Problem: `_as_utc`/`UTCDateTime` normalizes SQLite's naive datetimes only in the `RevisionDetails` projection. Every other ORM read of `created_at` stays naive on SQLite and aware on Postgres.
  - Fix: use a shared SQLAlchemy `TypeDecorator` on the `created_at` columns, or record why the projection is the chosen boundary.
- Snapshot freshness: current. The `docs/standards.md` sections for Python 3.14, FastAPI 0.143 and SQLAlchemy 2.1 match `docs/mobua-swe.md`.

### Spec (PASS)
- [minor] `src/news/service/drafts.py:313-320`
  - Source: AC-69, "Success is reported only after commit".
  - Problem: `plugin_draft.promoted` is logged inside the service, before the surface commits. On a failed commit the logs still show a promotion that was rolled back, followed by `api.database_failed`. Ticket 03's `plugin_draft.deleted` works the same way. Responses are correct.
  - Fix: either emit success events after commit, or record "events at flush time" in the spec or ADR. In both cases, pin the behavior in `test_api_commit_failure_reports_no_success_and_rolls_back`.
- [minor] `src/news/service/revision_history.py:86-91,157`
  - Source: the spec Observability list, which names only `plugin_draft.*` events for this flow.
  - Problem: `plugin_revision.selection_rejected` and `plugin.not_found` are not in the spec. `selection_rejected` also has `fields` but no safe `reason` code.
  - Fix: amend the Observability list and add a reason code (for example `unknown_revision`), or drop the events.
- [minor] `tests/service/test_promotion.py:259-269`
  - Source: AC-65, "Check state before rollback and committed state where applicable".
  - Problem: the failed-commit test checks committed state only after `session.rollback()`. Evidence line 73 overstates this.
  - Fix: assert `committed_state(engine) == before` after the failed commit and before the rollback.
- [minor] `tests/cli/test_revisions.py:210-232,250-272`
  - Source: AC-67, "Unknown, foreign-Reader, and wrong-Plugin Revision selections fail".
  - Problem: the CLI tests lack the "foreign Revision inside one's own Plugin" case and the `plugin_revision` INSERT commit failure. The API tests have both.
  - Fix: add the two parametrized cases.
- [minor] `tests/service/test_immutability.py`
  - Source: AC-68, "Manifest/code/ancestry/metadata remain immutable".
  - Problem: only `note` and `manifest` updates are exercised.
  - Fix: parametrize over `code`, `parent_revision_id`, `created_by` and `created_at`.

### Code-complete evidence (FAIL)
- [major] `src/news/service/drafts.py:280-286`, `evidence/04.md` "Not verified"
  - Source: code-complete item 1, "each failure mode" covered or justified.
  - Problem: concurrent promotions that read the same `max(number)` and compute the same `+1` are a real AC-66 failure mode ("distinct numbers"). The `(plugin_id, number)` unique constraint (`models.py:121`) should make one of them fail. The evidence says "There is no dedicated test" and gives no reason the case can't be tested.
  - Fix: use the existing `concurrent_write_before` harness to commit a same-number Revision on a second connection just before the INSERT. At the service level, assert the IntegrityError, the rollback and that state is unchanged. At the API level, assert a 503 with unchanged state.
- [minor] `tests/service/test_promotion.py:388,417`
  - Source: code-complete item 4, failure-mode logging tested.
  - Problem: the two race-conflict tests reach `plugin_draft.conflict` through the conditional-write branches without capturing logs.
  - Fix: wrap both in `capture_logs()` and assert the event's reason and ids.
- [minor] `evidence/04.md` AC-65, AC-66 and AC-81 sections
  - Source: code-complete item 2, red first per criterion.
  - Problem: these sections rely on one combined red summary, and the AC-81 logging was never shown red on its own.
  - Fix: add per-criterion red lines with short output excerpts.
- Resolved by this report: the old `report.md` still covered ticket 03 and had no promotion checks, which failed item 7.

## Criteria evidence
| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| AC-49 | `test_implementation`: exact pin accepted, lower bound rejected, non-exact rejected, no deps accepted, malformed metadata rejected; promotion/API/CLI invalid-Draft tests | yes | yes | yes (empty, no block, `[]`, CRLF) | yes (`===`, `==6.*`) | yes | yes |
| AC-65 | `test_promotion`: creates current Revision, flushed-not-committed, invalid Draft, stale version, failed commit, two races; API/CLI commit-failure tests | yes | yes; failed commit not checked before rollback | yes (future/stale version) | yes (races) | combined summary only | yes |
| AC-66 | sibling distinct numbers, older parent needs confirmation, reconfirmation, numbering after pointer rollback, pointer race; API/CLI confirmation tests | yes | **concurrent number allocation untested** | yes | yes | combined summary only | yes |
| AC-67 | `test_revision_history`: whole tree, select older creates nothing, outside-Plugin selections (unknown/other/foreign/Built-in), Reader scope; API/CLI select and reject tests; CLI/API history parity | yes | yes (CLI foreign-Revision partial) | yes | yes (Built-in) | yes | yes |
| AC-68 | `test_immutability`: delete rejected, bulk statements guarded, update tests, Channel Revision/Binding deletes allowed; no archive/delete in API or CLI | yes | partial (code/ancestry/metadata updates) | n/a: no ranges | yes (bulk ORM bypass) | yes | yes |
| AC-69 | API/CLI commit failure (503, empty stdout), 409/422 bodies, CLI stderr, no Test Run required | yes | yes | n/a: no ranges | yes | yes | yes |
| AC-81 | API stdout lifecycle-log test, CLI log-file test, exact event dicts in service tests; sentinel and requirement text absent | yes | yes (race conflicts not log-asserted) | n/a | yes (no leak to stdout) | not shown on its own | yes |

## Gates
| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass (0 errors) |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass (165 files formatted; 1 contract kept, 0 broken) |
| Full suite | `uv run pytest` | pass (409 tests, no warnings or skips) |
| Build | `uv build` | pass (sdist and wheel) |

No tests were deleted, skipped or weakened. One test was renamed with an identical body, and
the route-inventory test was tightened. The new tests use no mocks: races and commit failures
run on real migrated SQLite (a second connection and deferred-constraint triggers).

## Observability delivered
- Logs, all at info level through structlog. They carry only ids, reason codes and field names, with no Manifest, code, config or credentials:
  - `plugin_draft.promoted` (`drafts.py:313`)
  - `plugin_draft.rejected` (`drafts.py:262`)
  - `plugin_draft.conflict` (`drafts.py:126`, `revision_history.py:137`)
  - two events outside the spec, `plugin_revision.selection_rejected` and `plugin.not_found` (see Spec findings)
- Where the logs go: the CLI writes to its log file and the API to stdout, and tests cover both.
- Metrics: none, because the ticket says "No new metrics".

## Not verified
Code complete is not deployment verified. This review did **not** verify:
- Deployment, runtime behavior in the target environment, or real traffic and data.
- Postgres behavior of the conditional writes, the bulk-statement guard and the `IS NOT DISTINCT FROM` rendering (owned by ticket 21).
- Concurrent same-number promotion (see the major finding).
- Spec deployment checks 10 and 11, which were never run in a container.

## Deployment verification checklist
Evaluate manually or in the observability system to confirm the deployed change matches the intent of the spec or ticket.

- [ ] **Invalid Draft (spec check 10).** CLI/API: create a Reader Plugin, save a Draft whose PEP 723 block has `feedparser>=6`, then promote it.
  - Saving succeeds. Promotion fails with field errors.
  - Draft, Revisions and current pointer are unchanged.
  - `plugin_draft.rejected` (with `reason=invalid_implementation` and field codes) appears in the CLI log file or in `docker logs`.
- [ ] **Corrected promotion (spec check 10).** Pin `feedparser==6.0.11`, save and promote.
  - A new permanent Revision becomes current and only that Draft disappears.
  - `plugin_draft.promoted` shows the Reader, Plugin, Draft, parent and new Revision ids.
  - No Manifest, code or credential text appears in the logs.
- [ ] **Stale workspace (spec check 11).** Export a Draft, update it through the API, then run `draft promote --directory` on the stale workspace.
  - The command returns a conflict and no content is overwritten.
  - `plugin_draft.conflict` is logged.
- [ ] **History and selection (spec check 11).** View the Revision tree in both CLI and API, then select an older Revision.
  - Both show the same tree, and no new Revision is created.
  - Existing Channel Bindings stay on their pinned Revisions.
  - Promoting a Draft whose parent is no longer current requires confirming the current selection.
- [ ] **No deletion surface.** Confirm that no API route or CLI command archives or deletes a Plugin Revision. The OpenAPI route list has none.
