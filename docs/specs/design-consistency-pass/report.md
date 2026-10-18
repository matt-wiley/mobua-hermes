# Code-complete report: Design consistency pass (ticket 21)

- **Covers:** `c8298de436569a43bac4af48bdc2deaedb568498..9de31c8b05b27b199edd70540c66d23fdf24efb2` on branch `feat/docs-postgres-ci`.
- **Base selection:** ticket 21 is stacked on `feat/draft-promotion-and-ci` at `c8298de`. This range includes the shipping-plan update, ticket 21 implementation, parser repair, and accepted-exception documentation. Ticket 04 implementation is inherited; only its explicit Postgres isolation/race carry-over is reviewed here.
- **Spec:** `docs/specs/design-consistency-pass/spec.md`
- **Tickets:** `design-consistency-pass-21`, local status `done`; AC-55, AC-56, AC-58, AC-59 and the Postgres carry-over. This review does not change ticket status.
- **Sync:** n/a: `external: null`; no external tracker writes.
- **Date:** 2026-10-18.
- **Method:** three independent, fresh-context reviewers checked Standards, Spec, and Code-complete evidence without editing files. The parent independently ran the Postgres gate, actionlint, the real ADR checker, and the new parser reproduction. This report replaces the earlier review of `45b8d93`; implementation and repair evidence remain in their existing files.

## Verdict

**NOT CODE COMPLETE**: AC-56 still permits a duplicate ADR index entry to escape validation when its table row omits the leading pipe. Standards and Code-complete evidence reviews pass; Spec review fails. All executed green gates pass.

## Findings

No blockers. One major finding remains.

### Standards (PASS)

No findings. Parsing/comparison stays pure and filesystem I/O stays at the script edge. The Postgres isolation pin, portable test fixtures, and CI changes fit the ticket. Installed core stack majors match the standards snapshot; its historical test count does not make the configured commands stale. The accepted AC-59 historical test-order exception remains closed.

### Spec (FAIL)

- **[major] `scripts/check_adrs.py:171` — valid table rows without a leading pipe escape validation.**
  - **Source:** AC-56 requires the index to list “every ADR file exactly once, with matching title, status, and Amended-by values, and exits non-zero otherwise.”
  - `_table_rows` selects only lines whose stripped text starts with `|`. Markdown table data rows can omit the outer pipes, including in a table whose other rows have them. This is valid [GitHub Flavored Markdown table syntax, example 199](https://github.github.com/gfm/#example-199).
  - Appending the row below directly after the existing table rows creates a second ADR 0001 entry. The checker ignores it, returns no problems, and the filesystem command reports success. Thus the docs CI job also accepts the duplicate.

    ```markdown
    [0001](0001-channels-write-articles.md) | Channels write their own Articles | Accepted |  |
    ```

  - **Independent reproduction:** copy the real 26 ADRs and index to a temporary directory, append that duplicate without its leading pipe, then call `main([directory])`. Observed: `26 ADRs and index are consistent: <temporary directory>`, return `0`. The repository files were not modified. Both the parent and Spec reviewer also independently reproduced `check(...) == []` using synthetic ADRs.
  - **Fix:** use `/mobua-swe:fix` for ticket 21. Recognize table rows with optional outer pipes, or explicitly reject unhandled ADR rows rather than silently ignoring them. Add failing pure-check and filesystem regressions that assert the duplicate diagnostic, nonzero exit, and absence of a success summary. Preserve the existing first-row repair and all other diagnostics.

### Code-complete evidence (PASS)

No additional evidence/process findings. The missing behavior and regression coverage above prevent aggregate code completion despite this axis passing its history, recorded evidence, gate, and test-fidelity checks.

- The original AC-55/56 failing run and AC-58 backend/isolation failures remain recorded in `evidence/21.md`.
- For the first-row repair, history confirms tests-only `eac2b2e` precedes production-only `f4af4b7`. The evidence reviewer loaded the historical parser in memory and independently reproduced **8 failed, 39 passed in 0.10s**, for missing validation and diagnostics. All 47 current checker cases pass. The earlier first-row defect is repaired for its tested cases; the new optional-pipe defect above is distinct.
- AC-59's retrospective mutation run does not establish historical test-first order. The user's explicit, one-time acceptance is recorded in [ticket evidence](evidence/21.md#accepted-exception-ac-59-test-first-order-2026-10-18) and remains limited to the workflow/test ordering in `21746bf`. It waives no functional criterion, future TDD requirement, independent review, or hosted/deployment verification.
- No tests were deleted, weakened, skipped, or marked xfail. The commit-failure assertion was strengthened to `IntegrityError`. SQLite-specific PRAGMA assertions still run against an explicit SQLite fixture.
- Parser tests use synthetic inputs without mocks; filesystem tests use real temporary directories; database tests use real migrated connections, deferred constraints, and concurrent transactions. Each new boundary has appropriate integration coverage for the implemented scenarios.

## Criteria evidence

Only ticket 21's assigned criteria and explicit carry-over are assessed; later tickets in the full spec are not part of this verdict.

| Criterion | Actual tests / evidence inspected | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| AC-55 | `tests/scripts/test_check_adrs.py`: consistent metadata, missing/empty/repeated fields, malformed dates/amendments, reciprocal amendments, unknown targets, real ADRs | yes | yes | empty ADR set; metadata/body separation | multiple amendments; deterministic diagnostics | recorded 38-case failing checker run | yes |
| AC-56 | Same file: missing/duplicate/unknown entries, link/title/status/amendment mismatches, malformed rows, missing index; first-row and filesystem diagnostics/exit tests | yes | **incomplete: optional-pipe duplicate is ignored** | empty/missing index and directory; first entry without a header | header spacing; all discrepancies reported | original checker red; repair red independently reproduced | 47 existing cases pass; review probe confirms defect |
| AC-58 | `test_the_engine_fixture_uses_the_configured_database`; migrated `tests/service` fixtures; `test_migrated_schema_matches_the_models`, scope assertions, and `test_migration_downgrades_to_an_empty_database` | SQLite and Postgres | real repository rejection/rollback cases; recorded incompatible PRAGMA probe | isolated databases; migrated schema/scope | template cloning and cleanup | recorded backend mismatch and initial Postgres failures | 283 Postgres gate tests; 473 full SQLite tests |
| AC-59 | Six `tests/test_ci_workflow.py` cases: PR/main triggers, configured core commands, pinned Postgres service and URL, docs command, SHA pins, failure propagation | yes locally | recorded removed-job/unpinned-action mutation; failure propagation inspected | triggers and gate-command contract | independent jobs; pinned service/actions | historical ordering exception accepted; no claim of compliance | six contracts pass; actionlint clean; hosted behavior unverified |
| Ticket 04 carry-over | `test_connections_run_at_the_isolation_level_the_promotion_claim_needs`; four promotion races, including `test_a_promotion_overlapping_an_uncommitted_sibling_promotion_waits_then_conflicts` | READ COMMITTED pin | loser gets `stale_current_selection` | overlapping transaction waits | SERIALIZABLE database default; winner current; loser Draft retained; distinct numbers | recorded hostile-default five-failure run | passes on SQLite and Postgres |

Numeric ranges do not apply to workflow configuration; its boundaries are triggers and gate commands. Non-Postgres fixture URL rejection and the deliberately incompatible Postgres construct are recorded manual probes. Tests that deliberately create SQLite engines retain that backend; the real Postgres gate still exercises migrated repository/schema tests and promotion races. New application log/metric tests are inapplicable because the ticket explicitly requires diagnostic output and CI gate names instead.

## Gates

Executed independently for `9de31c8`; this report is the only subsequent repository edit.

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors, warnings, informations |
| Lint | `uv run ruff check .` | pass |
| Formatting | `uv run ruff format --check .` | pass: 177 files already formatted |
| Import boundaries | `uv run lint-imports` | pass: 1 kept, 0 broken |
| Full SQLite suite | `uv run pytest` | pass: 473 tests in 14.11 s |
| Postgres repositories/schema | `NEWS_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:55432/postgres uv run pytest tests/service tests/test_test_database.py` | pass: 283 tests in 20.27 s |
| ADR consistency | `uv run python -m scripts.check_adrs docs/adr` | pass: 26 ADRs and index consistent |
| Workflow syntax | `docker run --rm --volume /Users/matt/projects/mobua-hermes:/repo:ro --workdir /repo rhysd/actionlint:1.7.12 .github/workflows/core.yml` | pass: exit 0, no diagnostics |
| Diff whitespace | `git diff --check c8298de..9de31c8` | pass |

Postgres used a temporary local container on port 55432 with the exact CI image,
`postgres:18.6-alpine@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873`.
The container was stopped and automatically removed after the run. Postgres test databases
default to SERIALIZABLE, proving the engine's READ COMMITTED pin instead of inheriting
the server default.

The Standards reviewer also passed 55 focused SQLite tests, and the Spec reviewer passed
86 focused SQLite tests. These green results do not invalidate the independently
reproduced missing test case.

## Observability delivered

- Checker failures print file/field discrepancies to stderr and return nonzero; success prints a summary. Existing filesystem tests assert exact diagnostics and exit results. The optional-pipe case still bypasses this reporting, as described above.
- CI job names identify the failing gate: typecheck, lint, SQLite tests, Postgres tests, or docs.
- No new application events or metrics, as specified by ticket 21. Runtime metrics are not appropriate for this local documentation consistency check.

## Not verified

Code complete is not deployment verified. This review did **not** verify:

- Hosted GitHub Actions on `ubuntu-24.04`: Action execution, service health, PR/main triggering, or a deliberately broken index causing a hosted failure.
- The docs check on a deployed commit or runtime behavior with target-environment data and traffic.
- A full Postgres API/CLI suite in this review. The required repository/schema subset passed; implementation evidence separately records an earlier full Postgres run.
- Branch protection, web CI, hosted container integration tests, or image publishing; these are outside ticket 21.
- A fix for the new optional-pipe finding. This review changes only the report; it does not squash commits or change implementation.

## Deployment verification checklist

- [ ] On the deployed commit, run `uv run python -m scripts.check_adrs docs/adr`: exit 0 and all ADRs/index consistent.
- [ ] Open a PR and inspect the hosted `core` run: typecheck, lint, full SQLite suite, pinned Postgres repository/schema tests, and docs all execute and pass; the Postgres service becomes healthy.
- [ ] Merge through the normal process and confirm the same hosted gates execute and pass on a push to `main`.
- [ ] After fixing AC-56, use a test PR to remove an index row, change its status, and append a duplicate table row without a leading pipe: each mutation fails the hosted `docs` job with the affected file/field and no success summary; restoring the index passes.
- [ ] In the target Postgres environment, overlap two sibling promotions: one succeeds; the other waits, then returns 409 `stale_current_selection`; no deadlock or 503, winner current, losing Draft retained, distinct Revision numbers.
