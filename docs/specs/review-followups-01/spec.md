---
slug: review-followups-01
title: Follow-ups from the ticket 01 code review
status: draft
created: 2026-10-17
adrs:
  - docs/adr/0007-all-data-scoped-to-a-reader.md
  - docs/adr/0013-sqlite-default-postgres-ready.md
  - docs/adr/0016-config-and-plugins-as-revisioned-records.md
  - docs/adr/0017-service-layer-with-api-and-cli-surfaces.md
  - docs/adr/0018-plugin-bindings-pin-plugin-revisions.md
  - docs/adr/0019-built-in-plugins-are-shared-and-ejectable.md
external: null
---

# Follow-ups from the ticket 01 code review

## Intent
The code review of design-consistency-pass-01 (`docs/specs/design-consistency-pass/report.md`) found one major gap and a set of minor ones. The major gap, a Reader binding another Reader's Plugin Revision, is already fixed in `d664747`. This spec closes the minor findings before later tickets build on top of them:
- the Reader and Channel scoping rules are enforced by declaration, not guessed from foreign keys;
- Revisions are guarded against accidental updates;
- migrations ship inside the package;
- the CLI keeps its logs out of stdout and reports every failure cleanly;
- error types are named for what they hold;
- the tests assert what the criteria actually say.

It lands on `feat/design-consistency-pass` before design-consistency-pass-02 starts. Grill: `docs/specs/review-followups-01/grill.md`.

## Decisions
- **D-1:** a separate spec, landing before design-consistency-pass-02. Amendments to the design-consistency-pass spec or its ADRs, if any, link back to this grill. (grill 1)
- **D-2:** the `reader` table is not exempt from the Reader-id rule; its own `id` is its Reader id. Likewise, the `channel` table's own `id` is its Channel id. ADR 0007 and design-consistency-pass AC-53 stay as written. (grill 2, 3)
- **D-3:** every model declares its scope in SQLAlchemy `Table.info` as `{"scope": "app" | "reader" | "channel"}`.
  - The schema test checks every migrated table against these declarations.
  - `alembic_version` is the one known app-wide table that is not a model.
  - `plugin` and `plugin_revision` are `reader` tables whose `reader_id` is nullable for Built-in Plugins (ADR 0019).
  - `READER_SCOPE_EXEMPT_TABLES` is removed.

  (grill 3)
- **D-4:** Plugin Revisions, Channel Revisions and Plugin Bindings are guarded against updates by a service-layer ORM `before_flush` listener.
  - No designed path updates them: edits go to drafts (plugin-drafts spec) and a new Revision is inserted. The guard is a tripwire against accidental updates.
  - Deletes are not guarded.
  - The current-Revision pointer on Plugin and Channel rows stays updatable.

  (grill 4)
- **D-5:** migrations move into the package as `src/news/migrations/`, with `script_location = news:migrations`.
  - `migrate()` builds its Alembic config in code.
  - A root `alembic.ini` remains for developer autogenerate and points at the package location.
  - The core module glob in `docs/mobua-swe.md` changes from `alembic/**` to `alembic.ini`.
  - The ruff `known-third-party = ["alembic"]` setting is removed if it is no longer needed.

  (grill 5)
- **D-6:** the CLI writes service-layer logs to a file, as JSON lines, and the server keeps JSON on stdout. CLI stdout carries only command output. (grill 6)
  - **Location:** `--log-file` / `NEWS_CLI_LOG_FILE`. The default is `$XDG_STATE_HOME/news/cli.log`, falling back to `~/.local/state/news/cli.log`. The directory is created if missing.
  - **Growth:** the file is append-only, with no in-app rotation.
  - **Unopenable file:** the CLI fails fast before any work. It exits 1 and the stderr message names the path, the OS error and the override.
  - **Expected failures:** stderr shows the specific message, followed by `Logged to <path>.`.
  - **Unexpected exceptions:** a top-level handler logs `cli.unexpected_error` (the command, and `exc_info`). stderr shows one line, `Unexpected error: <Type>: <message>. Details logged to <path>.`, and the CLI exits 1.
  - **Standards:** the logging line in `docs/standards.md` (Repo overrides) is reworded to match.
- **D-7:** the service layer logs rejected user input at `info`, where the rejection is raised: `plugin_revision.rejected`, `channel.not_found`, `reader.not_found`. (grill 7)
- **D-8:** `require_reader(session, reader_id)` raises `ReaderNotFound` (a `LookupError`) for an unknown Reader. `create_plugin` and `create_channel` call it first. Channel operations already scope by Reader and report `channel.not_found`. (grill 8)
- **D-9:** service functions flush and never commit; the surface owns the transaction. CLI commands echo their result only after the transaction has committed. (grill 9)
- **D-10:** error types:
  - `ConfigError` is renamed `FieldError(field, message)` and moves to `service/validation.py`;
  - a base `ValidationRejected(Exception)` there holds `errors: list[FieldError]` and builds the message;
  - its subclasses are `ChannelRevisionRejected` and `PluginRevisionRejected` (renamed from `ManifestError`);
  - the CLI handles `ValidationRejected` in one place.

  (grill 10)
- **D-11:** tests assert the state a criterion names before any rollback. The schema scope rules live in a function in `tests/schema_rules.py`, which has its own unit tests on synthetic tables. (grill 11)
- **D-12:** the red-step convention (stub the unit, watch tests fail for a reason other than import or attribute errors, keep one red excerpt per slice) belongs in the mobua-swe plugin's `tdd` skill. It is changed separately in that repo. (grill 11)
- **D-13:** type-checker suppressions:
  - the CLI's uncommented `pyright: ignore` becomes a `cast` after the `isinstance` check;
  - `binding_config.py` gains one comment stating that jsonschema reports `required` and `additionalProperties` only on object instances;
  - the commented `iter_errors` ignore stays.

  (grill 12)
- **D-14:** Plugin drafts and test runs move to their own grill, `docs/specs/plugin-drafts/grill.md`. Their shape is already decided: a separate mutable working copy, promoted to an immutable Revision. That work lands before design-consistency-pass-03. (grill 14)
- **D-15:** each new log event is tested for emission and fields, and there are no new metrics. Deployment is verified through the CLI, the log file, the wheel and `docker logs` (see below). (grill 13)

## Scope and non-goals
**In scope:**
- Schema scope declarations and the schema rules (D-2, D-3).
- The Revision update guard (D-4).
- Moving the migrations, plus the `docs/mobua-swe.md` glob change (D-5).
- CLI file logging, fail-fast, pointers and the top-level handler, plus the `docs/standards.md` wording (D-6).
- The new service log events, and the Reader existence check (D-7, D-8).
- CLI echo after commit (D-9).
- Renaming the error types (D-10).
- Strengthening the tests named in D-11.
- The suppression cleanup (D-13).

**Non-goals:**
- Plugin drafts, Promote and test runs: the plugin-drafts spec (D-14).
- Guarding deletes of Revisions or Bindings: decided when Channel or Plugin deletion is specified.
- Log rotation in the app.
- Metrics.
- Changing the plugin's `tdd` skill or `code-complete.md`: a separate change in `mobua-claude-marketplace` (D-12).
- Setting `NEWS_CLI_LOG_FILE=/data/logs/cli.log` in the container image: the container ticket.
- API routes, Postgres runs (design-consistency-pass-21), and the cross-Reader Binding fix (already in `d664747`).

## Acceptance criteria

### Schema scope
- **AC-1:** Given the Alembic-migrated database, every table has a declared scope in `Table.info`, except `alembic_version`, which is treated as `app`. A migrated table with no declared scope is reported as a violation.
- **AC-2:** Given table descriptions (name, columns, foreign keys, declared scope), the schema rules report each of these as a violation:
  - a `reader` table without `reader_id`, except `reader`, whose `id` is its Reader id;
  - a `channel` table without `channel_id`, except `channel`, whose `id` is its Channel id;
  - an undeclared table;
  - a table with a foreign key to a `channel` table that is not itself declared `channel`;
  - a `channel` table without `reader_id`, since Channel records also carry their Reader id (ADR 0007). *Amended 2026-10-17 after the ticket 05 review.*
  - a declared scope other than `app`, `reader` or `channel` (D-3). *Amended 2026-10-17 after the ticket 05 review.*

  For a clean schema they report no violations.
- **AC-3:** The migrated database has no scope violations under AC-2's rules, and `READER_SCOPE_EXEMPT_TABLES` no longer exists.

### Revision immutability
- **AC-4:** Given a committed Plugin Revision, Channel Revision or Plugin Binding, when one of its attributes is changed and the session flushes, then `ImmutableRevisionError` is raised, naming the table and the changed attribute, and the stored row is unchanged.
- **AC-5:** Inserting new Revisions and Bindings, and moving a Channel's or Plugin's current-Revision pointer, still succeed while the guard is active.

### Migrations packaging
- **AC-6:** A wheel built by `uv build` contains `news/migrations/env.py` and at least one file under `news/migrations/versions/`.
- **AC-7:** `migrate()` upgrades a fresh SQLite database to head when the working directory is outside the repository.
- **AC-8:** From the repository root, Alembic's `check` command, run through the root `alembic.ini`, reports no differences between the models and the migrations.

### CLI logging
- **AC-9:** With `NEWS_CLI_LOG_FILE` or `--log-file` set, CLI log lines are written to that file. With neither set, they go to `$XDG_STATE_HOME/news/cli.log`, or `~/.local/state/news/cli.log` when `XDG_STATE_HOME` is unset. A missing directory is created.
- **AC-10:** Each log line in the file is a JSON object with `event`, `level` and `timestamp`. A second command appends to the file without removing earlier lines. During a command that logs, stdout carries only the command's output.
- **AC-11:** When the log file cannot be opened, the command exits 1 before touching the database, and stderr names the path, the OS error, and `--log-file` / `NEWS_CLI_LOG_FILE`.
- **AC-12:** An expected failure (a rejected validation, an unknown Channel, an unknown Reader) prints its specific message and then `Logged to <path>.` on stderr, and exits 1.
- **AC-13:** An unexpected exception during a command:
  - logs `cli.unexpected_error` at `error` level to the file, with the command name and the traceback;
  - prints exactly one stderr line, `Unexpected error: <Type>: <message>. Details logged to <path>.`;
  - if it happens before the log path is known (for example `Path.home()` fails), logs nothing, because logging is not configured and would reach stdout (D-6), and the line ends `No log file was open to record it.` instead;
  - shows no traceback on the terminal;
  - exits 1.
- **AC-14:** Without CLI configuration, `configure_logging()` still writes JSON lines to stdout, as the server needs.

### Service-layer failure logging and Reader check
- **AC-15:** When `create_plugin` rejects a Manifest, `PluginRevisionRejected` is raised, no Plugin or Plugin Revision row is created, and `plugin_revision.rejected` is logged at `info` with `reader_id` and `errors` (a list of field/message pairs).
- **AC-16:** When a Channel operation names a Channel that doesn't exist or isn't the Reader's, `ChannelNotFound` is raised and `channel.not_found` is logged at `info` with `reader_id` and `channel_id`.
- **AC-17:** When `create_plugin` or `create_channel` is given an unknown Reader id, `ReaderNotFound` is raised, no row is written, and `reader.not_found` is logged at `info` with `reader_id`. Through the CLI, stderr shows `no Reader <id>` and the command exits 1.

### Transactions
- **AC-18:** When a CLI command's commit fails (for example, a deferred constraint is violated at COMMIT), stdout is empty, the command exits 1 through the AC-13 path, and no row from the command persists.

### Error types
- **AC-19:** `ChannelRevisionRejected` and `PluginRevisionRejected` are both `ValidationRejected`.
  - Each carries `errors: list[FieldError]`.
  - Each has the message `"<field>: <message>"`, joined with `"; "`.
  - `ConfigError` and `ManifestError` no longer exist.

### Test strength
- **AC-20:** After a rejected Channel Revision save, and before any rollback, the session has no pending Channel Revision or Plugin Binding (`session.new` is empty), the Channel's current-Revision pointer is unchanged, and a separate connection sees the original Revision count.
- **AC-21:** A Plugin Revision saved with no Reader id and `created_by = creator_of(None)` reads back from the database with `created_by == "system"` and `reader_id IS NULL`.

## Design notes
- **Pure core:**
  - **Log path resolution:** a function of the environment mapping and the home directory, returning a `Path`, so no real environment or filesystem is needed in tests.
  - **`ValidationRejected` messages:** built from a list of `FieldError`s.
  - **Schema scope rules:** `tests/schema_rules.py` turns table descriptions into violations. It is test support, so it lives under `tests/`.
- **Edges:**
  - opening and appending the log file, and creating its directory;
  - the CLI's top-level exception handler and its transaction boundary;
  - the `before_flush` guard on the session;
  - Alembic's package-resource script location;
  - `uv build` for the wheel check.
- **Test seams:**
  - Log path resolution is unit-tested with explicit env and home values.
  - CLI behavior uses Typer's `CliRunner` with `NEWS_CLI_LOG_FILE` pointing into `tmp_path`.
  - The unopenable-file case uses a path under a read-only or non-existent parent.
  - Commit failure uses a trigger, added from a real second SQLite connection, that writes a dangling `DEFERRABLE INITIALLY DEFERRED` foreign key, so the flush succeeds and the COMMIT fails. Not a mock. (Amended in review: a second connection holding `BEGIN IMMEDIATE` fails the first INSERT at flush, which is now the separate flush-failure seam.)
  - The guard is tested on a real migrated SQLite session.
  - The schema rules get unit tests on synthetic descriptions, plus one integration test that feeds them the migrated database.
  - The wheel check builds into `tmp_path`. It is the one slower integration test.

## Observability
- **Logs** (structlog JSON lines; never Secrets, provider keys, Gateway Tokens or the Master Key):
  - `info` `plugin_revision.rejected`: `reader_id`, `errors`. The plugin-drafts spec adds `plugin_id` when Promote rejects a draft of an existing Plugin.
  - `info` `channel.not_found`: `reader_id`, `channel_id`.
  - `info` `reader.not_found`: `reader_id`.
  - `error` `cli.unexpected_error`: `command`, `exc_info`. Not written when the failure comes before the log path is known (AC-13). `command` names only the commands resolved so far.
  - `info` `channel_revision.rejected`: unchanged.
  - **Destination:** server process to stdout; CLI to its log file (D-6).
- **Metrics:** none. The design-consistency-pass spec allows only the four Gateway metrics, and these are low-volume user-input events that the logs already cover.

## Deployment verification checklist
- [ ] **CLI, invalid bind** (`news channel bind … --config '{}'`): exits 1 with the field error and `Logged to <path>.` on stderr, and stdout is empty. The log file has a `channel_revision.rejected` JSON line.
- [ ] **CLI, unknown Reader** (`news channel create --reader <random uuid> X`): prints `no Reader <id>` and exits 1, with no traceback on the terminal. The log file has `reader.not_found`.
- [ ] **CLI, unopenable log file** (`mkdir -m 500 /tmp/ro && NEWS_CLI_LOG_FILE=/tmp/ro/logs/cli.log news reader create A`, as a non-root user): exits 1 before any database write, naming the path and the override. As root, permissions don't block, so use a read-only mount instead.
- [ ] **Container, after the container ticket sets `NEWS_CLI_LOG_FILE=/data/logs/cli.log`:** CLI logs persist on the data volume across container restarts.
- [ ] **Clean venv** (`uv build`, `pip install dist/*.whl`, `news --database-url sqlite:///x.db db upgrade`): succeeds without a source checkout.
- [ ] **`docker logs <container>`:** server JSON lines on stdout, as before.
