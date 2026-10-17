# Code-complete report: Design consistency pass (ticket 01)

- **Covers:** `b1afb21..7e03878` on branch `feat/design-consistency-pass`
- **Spec:** `docs/specs/design-consistency-pass/spec.md`
- **Tickets:** design-consistency-pass-01 is `done`. Tickets 02–21 are `todo` and out of scope for this review.
- **Sync:** n/a. Every ticket has `external: null`.
- **Date:** 2026-10-17

## Verdict
**NOT CODE COMPLETE**: the Standards and Code-complete evidence axes both fail on one major finding. Saving a Channel Revision loads the Plugin Revision without scoping it to the Reader, so one Reader can bind another Reader's private Plugin Revision. This is untested, and a scratch run on SQLite confirmed it.

## Findings
Blockers first. No blockers were found.

### Standards
- **[major]** `src/news/service/channels.py:121-126` (`_binding_errors`)
  - Source: docs/standards.md, Repo overrides, core: "Scope every row by Reader, and by Channel where it belongs to one. Enforce this in the service layer". Also ADR 0018: "A Binding may only reference Revisions of Plugins owned by the Channel's Reader, or of Built-in Plugins".
  - Problem: `session.get(PluginRevision, id)` doesn't check the owner. Validation errors also expose the other Reader's config schema.
  - Fix: accept only a Plugin Revision whose `reader_id` is the acting Reader's id or `NULL` (a Built-in). Otherwise report `bindings.N.plugin_revision_id: no such Plugin Revision`. Write the test red-first.
  - Note: the Spec axis files the same issue as minor, because AC-4 belongs to ticket 05. It still counts as major here: the repo's standards rule applies now, and the shipped CLI exposes it.
- **[minor]** `src/news/cli/main.py:88,105,115,133`
  - Source: baseline §5, "no silent fallbacks".
  - Problem: success output is echoed inside the transaction, before the commit. If the commit fails, the user has already been told it succeeded.
  - Fix: echo after the `with` block exits.
- **[minor]** `src/news/cli/main.py:107,136-138`
  - Source: baseline §5, "logged with context".
  - Problem: `ManifestError` and `ChannelNotFound` are written to stderr but never logged.
  - Fix: log them in the service layer with the Reader and Channel ids.
- **[minor]** `src/news/cli/main.py:73`
  - Source: baseline §1, "comments say why".
  - Problem: there's a `pyright: ignore` with no reason given.
  - Fix: use `cast` after the `isinstance` check, or add a one-line why.
- **[minor]** `src/news/service/binding_config.py:47-56`
  - Problem: the `cast`s are sound, but the invariant behind them isn't stated: `required` and `additionalProperties` errors only occur on object instances.
  - Fix: add a one-line comment.
- **[minor]** `src/news/service/manifest.py:12-15`, `channels.py:23-26`
  - Source: baseline §1, "Names carry the meaning".
  - Problem: Manifest errors reuse `ConfigError`, a type documented as a *Binding*-config error. The two exception `__init__` methods are also duplicates.
  - Fix: rename it to a neutral `FieldError`.
- **[minor]** `src/news/service/db.py:10-11`
  - Source: baseline §4.
  - Problem: `ALEMBIC_INI` resolves to the source tree, so `news db upgrade` fails when run from a built wheel.
  - Fix: move migrations into the package, or record that migrations only run from a source checkout (e.g. in an ADR, or in the container ticket).
- **Snapshot staleness:** not stale. The resolved versions are inside the snapshot majors.

### Spec
- **[minor]** `tests/service/test_channels.py:77,154`, `tests/cli/test_cli.py:130`
  - Source: AC-1, "no Channel Revision is created".
  - Problem: these tests count Revisions only after a rollback, so they would miss a Revision that was flushed and then rolled back.
  - Fix: count, and check `current_revision_id`, before any rollback.
- **[minor]** `tests/service/test_plugins.py:39-41`
  - Source: AC-5, system path.
  - Problem: only the pure `creator_of(None)` is tested.
  - Fix (optional): add a repository round-trip of a `reader_id=NULL`, `created_by="system"` row.
- **[minor]** `tests/service/test_schema.py:12,44-59`
  - Source: AC-53, "Every table for Channel-owned records also has a Channel id column".
  - Problem: the foreign-key heuristic skips `channel_revision` and any table that is Channel-owned only indirectly.
  - Fix: assert `channel_revision` explicitly, and either declare the Channel-owned tables or follow foreign-key chains.
- **[minor]** `src/news/service/models.py:15-18`
  - Source: AC-53 and D-18 allow only "Built-in Plugin tables and declared app-wide tables".
  - Problem: the `reader` exemption fits neither category.
  - Fix: record it in ADR 0007 or the spec, or treat `reader.id` as the table's Reader id.
- **[minor]** `src/news/service/models.py`
  - Source: D-2, "immutable … Revisions".
  - Problem: immutability is a convention and nothing enforces it.
  - Fix (optional): add a `before_update` guard, or record the convention.
- **Scope:** nothing beyond the ticket. `db upgrade` and `reader create` are needed for the CLI to work.

### Code-complete evidence
- **[major]** The cross-Reader Plugin Revision case is not tested.
  - This is the same issue as the Standards major, recorded here as an evidence gap under AC-1's failure modes.
- **[minor]** `tests/service/test_schema.py:28-37`
  - Problem: no recorded red shows the Reader-id check failing on a table without `reader_id`. On the empty red database it passed vacuously.
  - Fix: record a temporary-mutation check in the evidence, or unit-test the check on a throwaway schema.
- **[minor]** `evidence/01.md`, AC-1 service red
  - Problem: the red is recorded as a count only, against `NotImplementedError` stubs.
  - Fix: include a trimmed excerpt next time, preferably from stubs that return instead of raising.
- **[minor]** `src/news/cli/main.py:91-115`
  - Problem: passing a `--reader` id that doesn't exist dumps a raw `IntegrityError` traceback.
  - Fix: print "no Reader <id>" and exit 1, with a CLI test.
- **[minor]** `src/news/service/observability.py:18`
  - Problem: JSON logs and CLI output share stdout. The CLI tests take the last line as a workaround.
  - Fix (optional): send CLI logs to stderr, or document the split. Assert the rejected log line once at CLI level.

## Criteria evidence
| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| AC-1 | `test_binding_config.py` (8); `test_manifest.py` (9); `test_channels.py`: `test_binding_with_valid_config_creates_a_pinned_revision`, `test_binding_missing_a_required_field_is_rejected_and_no_revision_is_created`, `test_rejected_revision_is_logged_with_the_channel_and_errors`, `test_unknown_field_is_rejected_when_the_schema_forbids_it`, `test_unknown_field_is_kept_when_the_schema_allows_it`, `test_binding_to_a_missing_plugin_revision_is_rejected`, `test_one_invalid_binding_rejects_the_whole_revision`, +5; `test_cli.py` (7) | yes | partial: cross-Reader Plugin Revision untested (major); "no Revision" only asserted after rollback (minor) | yes | yes | yes | yes |
| AC-5 | `test_revision_created_by_a_reader_records_that_readers_id`, `test_revision_created_without_a_reader_records_system_as_creator`, `test_created_plugin_is_owned_by_the_reader_with_a_first_revision`, `test_plugin_with_an_invalid_manifest_is_rejected_and_not_saved`, `test_revisions.py` (3) | yes | yes | yes (first number) | n/a: two-valued rule | yes | yes |
| AC-53 | `test_schema.py` (8) | yes | not demonstrated failing (minor) | partial: `channel_revision` not checked (minor) | yes (drift, stale exemptions, non-vacuous) | yes | yes |
| ADR 0017 layering | import-linter `layers` contract | yes | yes (violations injected, reported broken) | n/a | n/a | yes | yes |

## Gates
Each reviewer ran these independently.

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass (strict, 0 errors) |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass (1 contract kept) |
| Full suite | `uv run pytest` | pass (53 tests, 0 skipped) |
| Build | `uv build` | pass |

## Observability delivered
- **Logs:**
  - `info channel_revision.rejected`, with `channel_id` and `errors`, written as structlog JSON on stdout. Tested at service level with `capture_logs`, and JSON formatting is tested separately.
  - Other failures (invalid Manifest, unknown Channel, unknown Reader) are not logged (minor).
- **Metrics:** none. The spec allows only the four Gateway metrics, which belong to tickets 09–11.

## Not verified
Code complete is not deployment verified. This review did **not** verify:
- Deployment, runtime behavior in the target environment, or real traffic and data.
- Postgres. Repository and schema tests ran on SQLite only, and AC-58 is ticket 21.
- Running `news db upgrade` from an installed wheel or the container image. It is known to depend on the source-tree `alembic/` folder.
- SQLite WAL behavior with the CLI and the server process writing at the same time.

## Deployment verification checklist
Evaluate manually or in the observability system to confirm the deployed change matches the intent of the spec or ticket.

- [ ] **`news db upgrade` on a fresh volume** (`news --database-url sqlite:////data/news.db db upgrade`): prints "Database is up to date.", and `sqlite3 /data/news.db 'PRAGMA journal_mode'` returns `wal`.
- [ ] **Create commands** (`news reader create Ada`, then `news plugin create --reader <id> --manifest manifest.toml --code main.py`, then `news channel create --reader <id> Local`): each prints an id and exits 0.
- [ ] **Valid bind** (`news channel bind … --config '{"url":"https://example.com/rss"}'`): prints "Saved Channel Revision 2.".
- [ ] **Invalid bind** (`news channel bind … --config '{}'`): exits 1 and prints `bindings.0.url: 'url' is a required property` on stderr. `SELECT count(*) FROM channel_revision WHERE channel_id=…` is unchanged.
- [ ] **Rejection log** (`docker logs <container>` or the CLI's stdout): one JSON line with `"event": "channel_revision.rejected"`, `"level": "info"`, the `channel_id` and the `errors` list.
- [ ] **Malformed config** (`--config '[1]'` and `--config '{url:'`): exit 2 with "must be a JSON object" and "not valid JSON".
- [ ] **Creator** (`SELECT created_by FROM plugin_revision`): returns the creating Reader's id.
- [ ] **After the major fix, cross-Reader bind:** binding another Reader's Plugin Revision is rejected with `bindings.0.plugin_revision_id`.
