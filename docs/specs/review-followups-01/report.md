# Completion report: review-followups-01

- **Implementation covered:** `945315f..c4b0769cfb5fea8cc3aabd41b4109e52bf7917ed` on `feat/design-consistency-pass--codex-test`.
- **Spec:** [spec.md](spec.md), status `done`.
- **Tickets:** review-followups-01-01 through review-followups-01-06, all `done`.
- **Sync:** n/a; all six tickets have `external: null`. No external tracker updates were made.
- **Date:** 2026-10-17.

## Verdict

**CODE COMPLETE:** all six tickets have passing reviews and collectively cover AC-1 through AC-21. The last outstanding major, ticket 06's pending current-Revision relationship assertion gap, is fixed and independently re-reviewed. The latest configured gates passed, including 147 tests.

This closeout consolidates completed ticket reviews; it is not a new independent review of the entire implementation. The earlier reviews' minor findings remain recorded as non-blocking follow-ups. Code complete is not deployment verified.

## Review provenance and criterion coverage

The complete ticket reports are preserved under `reviews/`, including their findings, test mappings, category explanations, gate results and verification limits. Historical reports retain the state and line numbers at which they were written; later work may supersede individual findings.

| Ticket | Acceptance criteria | Passing review source | Evidence |
|---|---|---|---|
| [01: CLI log file](tickets/01-cli-logs-to-a-file.md) | AC-9, AC-10, AC-11, AC-14 | [reviews/01.md](reviews/01.md), from `01e4f81` | [evidence/01.md](evidence/01.md) |
| [02: CLI failures and transaction output](tickets/02-cli-error-reporting-and-commit-order.md) | AC-12, AC-13, AC-18 | [reviews/02.md](reviews/02.md), from `a13fabd` | [evidence/02.md](evidence/02.md) |
| [03: Validation errors and service failures](tickets/03-error-types-service-logging-and-reader-check.md) | AC-15, AC-16, AC-17, AC-19 | [reviews/03.md](reviews/03.md), from `d16e591` | [evidence/03.md](evidence/03.md) |
| [04: Packaged migrations](tickets/04-migrations-inside-the-package.md) | AC-6, AC-7, AC-8 | [reviews/04.md](reviews/04.md), from `b8af337` | [evidence/04.md](evidence/04.md) |
| [05: Declared table scopes](tickets/05-declared-table-scopes.md) | AC-1, AC-2, AC-3, AC-21 | [reviews/05.md](reviews/05.md), from `b829abe` | [evidence/05.md](evidence/05.md) |
| [06: Revision guard and rejection checks](tickets/06-revision-update-guard-and-rejection-tests.md) | AC-4, AC-5, AC-20 | [reviews/06.md](reviews/06.md), preserved at `c4b0769` | [evidence/06.md](evidence/06.md) |

All 21 criteria have an owner and a passing review; all declared ticket dependencies are done. Categories that do not apply and the recorded red steps are explained in the linked reports/evidence rather than inferred from a passing test count.

Ticket 06 was reviewed at pre-squash head `036d8b6`. The reviewed file tree was verified unchanged after its follow-up commits and passing report were squashed into `c4b0769`. The backup branch `backup/feat/design-consistency-pass--codex-test-presquash-20261017-184952` preserves those commits and the historical report references.

## Findings carried forward

No unresolved blocker or major remains in the passing ticket reviews. This closeout does not claim that all earlier minor findings were fixed. Their full sources and suggested fixes are retained in the archived reports.

### Standards

- [Ticket 01](reviews/01.md): CLI help/completion can open the log file, default help text is manual, and the repo configuration's observability wording/test-count comment needs refreshing.
- [Tickets 01–03](reviews/01.md): standards-library coverage for dependencies such as Typer, structlog, jsonschema, Pydantic and Alembic remains follow-up work. The configured stack's majors match the pinned snapshot; missing library entries were not treated as blockers.
- [Ticket 03](reviews/03.md): binding-config comment placement and Reader attribution on the existing Channel rejection log were noted. Ticket 02 addressed some earlier message-format duplication; the original findings remain available.
- [Ticket 04](reviews/04.md): the developer Alembic path could report a missing `NEWS_DATABASE_URL` more clearly. Disposal and config cleanup were accepted as justified.
- [Ticket 05](reviews/05.md): redundant schema assertions and the test checking an old name's absence were accepted as minor.

### Spec

- [Tickets 01 and 03](reviews/01.md): document empty/relative XDG handling and the `(root)` validation-message convention more explicitly; improve the unopenable-file message for an `OSError` without `strerror`.
- [Ticket 04](reviews/04.md): migration tests could explicitly pin their working directory and independently establish the expected migration head.
- [Ticket 05](reviews/05.md): the foreign-key-target test can be strengthened to distinguish migrated-database inspection from model metadata; ticket 05's verification bullets can be aligned with the two amended scope rules.
- Ticket 02 records its minor fixes and their limits in [reviews/02.md](reviews/02.md). The pending-pointer finding from ticket 06 is closed by the independently verified relationship assertion before autoflush and foreign-key recheck afterward.

### Code-complete evidence

- [Ticket 01](reviews/01.md): root execution of the permission test, an existing database remaining untouched, directory-path error assertions, default-path command assertions and an empty log-file environment variable were noted as additional test coverage opportunities.
- [Ticket 05](reviews/05.md): a modelled table with missing scope metadata lacks its own integration case; the main evidence test count predates two later cases.
- Earlier per-evidence deployment-checklist gaps are covered by the archived reports and the consolidated checklist below. Historical red execution cannot be authenticated from Git; the ticket 06 relationship mutation was independently reproduced during review.
- Existing server logging initialization and container log persistence remain deployment follow-ups. No production/server/container behavior is certified here.

These are retained follow-ups, not new acceptance criteria or claims of newly re-tested defects. No production or test code changed during closeout.

## Gates

The latest independent ticket 06 review ran the complete configured gates against the implementation now represented by `c4b0769`:

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass, 0 errors and 0 warnings |
| Lint | `uv run ruff check .` | pass |
| Formatting | `uv run ruff format --check .` | pass, 119 files already formatted |
| Layering | `uv run lint-imports` | pass, 1 contract kept, 0 broken |
| Full suite | `uv run pytest` | pass, 147 tests, including wheel packaging |

The Standards and Spec reviewers also independently ran 57 tests in the affected files. The Spec review's scratch pointer mutation caused both service rejection tests to fail at the expected assertion.

This closeout changes Markdown only. Checks performed for closeout: all tickets are done, declared dependencies are satisfied, acceptance-criterion coverage is exactly AC-1 through AC-21, archived reviews match their source reports, local Markdown links resolve, and `git diff --check` passes. Runtime gates were not repeated for this documentation-only change.

## Observability delivered

- CLI logs append JSON lines to `--log-file` / `NEWS_CLI_LOG_FILE`, defaulting under `$XDG_STATE_HOME/news/` or `~/.local/state/news/`. CLI stdout carries command results only.
- Service failure events: `plugin_revision.rejected` with Reader/errors, `channel.not_found` with Reader/Channel, and `reader.not_found` with Reader, all at `info`. Existing `channel_revision.rejected` remains.
- Unexpected CLI exceptions produce `error cli.unexpected_error` with command and traceback, except before a log path is available. Expected failures give their message and log-file pointer.
- The default `configure_logging()` stdout behavior remains tested for server use; actual server initialization is not verified by this closeout.
- No new metrics, as specified. The guard propagates a contextual programming error through the existing CLI unexpected-error handler.
- In-place plain JSON mutation is not tracked; whole-value reassignment is tracked and rejected. Deletes and direct bulk/raw SQL enforcement are outside the guard's scope.

## Not verified

Code complete is not deployment verified. This closeout did **not** verify:

- Deployment, production traffic/data, container startup, server logging initialization or persistent container CLI logs.
- Postgres; dedicated validation belongs to design-consistency-pass-21.
- Installed-wheel behavior in the target environment. Automated packaging checks and the earlier local smoke are documented in ticket 04.
- Real disk-full or I/O failures at COMMIT; tests use a deferred foreign-key violation to exercise commit failure and a separate lock to exercise flush failure.
- Actual historical execution of recorded red runs, or independent re-review of every minor fix described in the earlier reports.
- A live CLI command specifically triggering `ImmutableRevisionError`; the guard and generic CLI handler are tested separately.
- Work explicitly excluded by the spec: plugin drafts, container image configuration, metrics and API routes.
- Resolution of the retained minor findings. They do not block the existing passing ticket verdicts.

## Deployment verification checklist

Use disposable data for failure and mutation checks. Record the target environment and results when performing these checks.

- [ ] **Installed wheel:** build/install into a clean Python 3.14 venv outside the source checkout. Run `news --database-url sqlite:///x.db db upgrade` twice; both exit 0. The database reports migration `d2ebcc45139c`, and CLI stdout carries only command output.
- [ ] **Developer migration path:** from the repository root, point `NEWS_DATABASE_URL` at a migrated disposable database and run `uv run alembic check`; expect no new upgrade operations.
- [ ] **Successful writes:** create a Reader, Plugin and Channel, then bind a valid Plugin Revision. Output reports success and independent queries observe the committed rows/current Revision.
- [ ] **Invalid bind:** missing required config exits 1 with empty stdout, field errors and `Logged to <path>.` on stderr. The JSON log contains `channel_revision.rejected`. Revision/Binding counts and the current pointer stay unchanged.
- [ ] **Unknown Reader/Channel and invalid Manifest:** exercise each CLI path. Expect exit 1, its specific error and log pointer, the appropriate `reader.not_found`, `channel.not_found` or `plugin_revision.rejected` JSON event with contextual fields, and no new rows. Another Reader's Channel is treated as unavailable.
- [ ] **Log destination/append:** explicit option overrides the environment; unset both to check XDG/home fallback. Log entries contain `event`, `level` and `timestamp`; a second logging command appends without removing earlier entries.
- [ ] **Unopenable log file:** as a non-root user use an unwritable parent; as root use a read-only mount. Expect exit 1 before database work, with path, OS error and overrides on stderr. Check both a nonexistent database and an unchanged existing database.
- [ ] **Unexpected failure:** hold a SQLite write lock from another connection, run a writing CLI command, then release the lock. Expect exit 1, empty stdout, one unexpected-error stderr line and `cli.unexpected_error` containing command/traceback; no inserted row persists. On disposable data, separately exercise a deferred-constraint COMMIT failure and expect the same absence of success output/persisted rows.
- [ ] **ORM guard:** change a committed Plugin Revision, Channel Revision and Plugin Binding in turn; flush raises `ImmutableRevisionError` naming table/attribute. Roll back and independently verify unchanged rows. New Revisions/Bindings and allowed current-pointer moves succeed.
- [ ] **Container follow-up:** once the container ticket configures `NEWS_CLI_LOG_FILE=/data/logs/cli.log`, verify CLI log persistence across restarts and server JSON on `docker logs <container>`, with no new migration/model warnings.
