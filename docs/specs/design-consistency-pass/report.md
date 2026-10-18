# Code-complete report: Design consistency pass (ticket 21)

- **Covers:** `c8298de436569a43bac4af48bdc2deaedb568498..45b8d93250dfd809dbfa744bcab1f6e9a1998c61` on branch `feat/docs-postgres-ci`.
- **Base selection:** this is the ticket 21 stacked branch. Its parent, `feat/draft-promotion-and-ci`, ends at `c8298de`; the range includes the shipping-plan update `9b0abb6` and all four ticket 21 commits. Ticket 04 implementation is inherited and is not re-reviewed as new scope.
- **Spec:** `docs/specs/design-consistency-pass/spec.md`
- **Tickets:** `design-consistency-pass-21`, local status `done`; AC-55, AC-56, AC-58, AC-59 and ticket 04's Postgres isolation/race carry-over. The status is not changed by this review.
- **Sync:** n/a: `external: null`; no external tracker writes.
- **Date:** 2026-10-18.
- **Method:** three independent, fresh-context reviewers checked Standards, Spec, and Code-complete evidence. The parent independently ran Postgres, actionlint, the real ADR checker, and the reported parser reproduction. This replaces the earlier ticket 04 report as required by the review workflow; ticket 04 evidence and its separate follow-up reports remain in the repository.

## Verdict

**NOT CODE COMPLETE**: AC-56 has a confirmed false negative, and AC-59's disclosed retrospective red run does not satisfy the workflow's strict test-first requirement. All executed green gates pass.

## Findings

No blockers. Two major findings remain.

### Standards (PASS)

No substantive findings. ADR parsing/comparison is pure, filesystem effects stay at the script edge, and the Postgres isolation pin and fixture changes fit the ticket's scope. Installed core dependency majors match the standards snapshot; the historical test count in `docs/mobua-swe.md` does not make the commands or stack stale. The test-first exception is recorded under evidence below rather than duplicated here.

### Spec (FAIL)

- **[major] `scripts/check_adrs.py:172` — the first index entry can escape validation.**
  - Source: AC-56 requires that the index “lists every ADR file exactly once, with matching title, status, and Amended-by values, and exits non-zero otherwise.”
  - `_table_rows` always discards the first pipe-delimited line, without checking that it is the table header. If the header is replaced with an ADR entry, that entry is invisible to counting and field validation. An index containing the same ADR entry in that position and in the body passes.
  - Reproduction against the reviewed code: for `0001-use-sqlite.md` with matching title/status/date, use the index below. `check(files, index)` returns `[]`.

    ```markdown
    | [0001](0001-use-sqlite.md) | Use SQLite | Accepted | |
    |---|---|---|---|
    | [0001](0001-use-sqlite.md) | Use SQLite | Accepted | |
    ```

  - Fix in ticket 21 through `/mobua-swe:fix`: recognize or validate the header explicitly, validate/count every actual ADR row, and add a failing regression for a missing/replaced header with a duplicate or incorrect first entry. Keep the existing exact diagnostic and CLI exit assertions.

### Code-complete evidence (FAIL)

- **[major] `docs/specs/design-consistency-pass/evidence/21.md:173` — AC-59 was implemented before its test.**
  - Source: baseline standards §3 and the TDD cycle require “No production code without a failing test first”; code-complete item 2 requires red-first evidence for each criterion.
  - The evidence honestly states that the workflow YAML preceded its contract test. The subsequent mutation run demonstrates meaningful missing-behavior failures, but cannot establish historical test-first order. This is a process/evidence failure, not a claim that the workflow lacks tests or a recorded failing run.
  - Commit `21746bf` includes the workflow and its tests together, satisfying the separate history check that tests land before or with implementation.
  - Resolution: retain the accurate disclosure. No retrospective run or rewritten evidence can change the chronology. Under the invoked workflow this remains an exception requiring explicit user acceptance before it can be treated as satisfied; this review does not grant that exception. Future corrective slices must use test-first order.

## Criteria evidence

The full spec spans later tickets. This review checks only ticket 21's assigned criteria and its explicit carry-over.

| Criterion | Tests / evidence | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| AC-55 | `tests/scripts/test_check_adrs.py`: consistent ADRs, missing/empty/duplicate metadata, malformed dates, reciprocal amendments in both directions, unknown targets, malformed amendment lists, real ADRs | yes | yes | empty ADR set; header/body separation | multiple amendments; deterministic diagnostics | recorded 38 failing cases against missing implementation | yes |
| AC-56 | Same file: missing/duplicate/extra rows, wrong links/titles/status/amendments, malformed cells, missing index; `test_the_script_reads_a_directory_and_exits_nonzero_on_problems` checks exact stderr and return code | yes | partial: first-row bypass above | empty index; missing directory/index | all discrepancies reported together | same recorded checker red run | existing tests pass; review probe exposes gap |
| AC-58 | `test_the_engine_fixture_uses_the_configured_database`; `tests/service` through migrated shared fixtures; `test_migrated_schema_matches_the_models`, scope tests and `test_migration_downgrades_to_an_empty_database` | both backends | real repository rejection/rollback tests; incompatible PRAGMA probe recorded | fresh database per test; schema/scope boundaries | template migration and cleanup | backend mismatch and initial Postgres failures recorded | 283 Postgres tests; 464 SQLite tests |
| AC-59 | `tests/test_ci_workflow.py`: `test_it_runs_on_every_pull_request_and_every_push_to_main`, `test_each_core_gate_runs_in_its_own_job`, pinned Postgres job, docs command, full-SHA Actions, `test_no_step_or_job_is_allowed_to_fail` | local workflow contract | recorded mutation removes jobs/unpins Action; standard Actions failure propagation inspected | PR and main triggers; gate-command contract | pinned image/actions; independent jobs | retrospective only; exception above | 6 contract cases; actionlint clean; hosted CI unverified |
| Ticket 04 carry-over | `test_connections_run_at_the_isolation_level_the_promotion_claim_needs`; four race tests in `test_promotion.py`, including `test_a_promotion_overlapping_an_uncommitted_sibling_promotion_waits_then_conflicts` | READ COMMITTED pin | losing promotion gets `stale_current_selection` | second connection waits on uncommitted sibling | SERIALIZABLE database default; winner retained, loser Draft retained, distinct numbers | hostile-default five-failure run recorded | passes on SQLite and Postgres |

Category applicability: numeric input/output ranges are not relevant to workflow configuration. Its boundaries are trigger configuration and gate commands. Fixture configuration rejection for a non-Postgres URL and a deliberately incompatible Postgres construct are recorded manual probes rather than committed regression tests. SQLite-specific PRAGMA and file/lock tests intentionally retain SQLite engines; this is documented and does not replace the migrated Postgres schema/repository run.

## Gates

Executed independently against `45b8d93`; the subsequent report edit does not alter implementation or tests.

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors, warnings, informations |
| Lint | `uv run ruff check .` | pass |
| Formatting | `uv run ruff format --check .` | pass: 176 files already formatted |
| Import boundaries | `uv run lint-imports` | pass: 1 kept, 0 broken |
| Full SQLite suite | `uv run pytest` | pass: 464 tests, 10.91 s |
| Postgres repositories/schema | `NEWS_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/postgres uv run pytest tests/service tests/test_test_database.py` | pass: 283 tests, 15.35 s |
| ADR consistency | `uv run python -m scripts.check_adrs docs/adr` | pass: 26 ADRs and index consistent |
| Workflow syntax | `docker run --rm --volume /Users/matt/projects/mobua-hermes:/repo:ro --workdir /repo rhysd/actionlint:1.7.12 .github/workflows/core.yml` | pass: exit 0, no diagnostics |

Postgres used a temporary local container with the exact CI image, `postgres:18.6-alpine@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873`, on port 55432. The review stopped and automatically removed it after the run.

No tests were deleted, weakened, skipped, or marked xfail. Implementation commits include their corresponding tests. New pure-core tests use synthetic inputs without mocks; filesystem checks use real temporary directories; database rejection and race tests use real migrated connections and deferred constraints. The implementation evidence records a successful build and a full Postgres suite, but this review independently reran only the required Postgres repository/schema subset.

## Observability delivered

- The checker prints file/field discrepancies to stderr, returns nonzero on failure, and prints a summary on success. Tests assert the exact error output and return values.
- CI jobs identify the failing gate: typecheck, lint, SQLite tests, Postgres tests, or docs.
- No new app events or metrics, as explicitly required by this ticket. Metrics would not add useful runtime measurement to this local consistency check.

## Follow-up status (2026-10-18)

The findings and verdict above describe the reviewed `45b8d93` snapshot. The parser major
was subsequently repaired by `f4af4b7`, after failing regressions were committed in
`eac2b2e`. The focused suite now passes 47 cases and the full SQLite suite passes 473;
typecheck, lint, formatting, import boundaries and the current ADR check also pass.
See [the fix report](../fix-adr-index-first-row/report.md) for red/green evidence.

The historical AC-59 test-first finding remains open. Its original disclosure is preserved,
and no user override or independent review of the repair is claimed. The overall ticket
therefore remains **NOT CODE COMPLETE** under the strict workflow.

## Not verified

Code complete is not deployment verified. This review did **not** verify:

- Hosted GitHub Actions execution on `ubuntu-24.04`, including Action execution, service health, PR/main triggering, or a broken index causing a hosted failure.
- The docs check on a deployed commit, or real runtime behavior with target-environment data and traffic.
- Branch-protection requirements, web CI, container integration execution in hosted CI, or image publishing; these are outside ticket 21.
- A full Postgres API/CLI suite in this independent review. The required repository/schema subset and its promotion races passed; the implementation evidence separately records a full Postgres run.

## Deployment verification checklist

- [ ] On the deployed commit, run `uv run python -m scripts.check_adrs docs/adr`: exit 0 and all ADRs/index consistent.
- [ ] Open a PR and inspect the hosted `core` run: typecheck, lint, full SQLite suite, pinned Postgres repository/schema tests, and docs all execute and pass; the Postgres service becomes healthy.
- [ ] Push a commit to `main` through the normal merge process and confirm the same hosted gates execute and pass.
- [ ] In a test PR, remove an ADR index row or change its status: the hosted `docs` job and overall run fail with the affected file/field; restoring it makes the check pass.
- [ ] In the target Postgres environment, overlap two sibling promotions: one succeeds and the other waits, then returns 409 `stale_current_selection`; no deadlock or 503, winner current, losing Draft retained, and distinct Revision numbers.
