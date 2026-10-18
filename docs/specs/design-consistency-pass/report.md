# Code-complete report: Design consistency pass (ticket 03)

- **Covers:** `e76d2df..1e66aa2` on branch `feat/design-consistency-pass`.
- **Branch merge-base:** `b1afb214eb1e3b059373079ad2fa2a2c5f4f55d9` with `main`. This review covers only ticket 03's commits:
  - Original work: `7205191`, `705a5d8`, `79483f3`, `1128362`.
  - The previous review report: `2176d50`.
  - Fixes made after that review: `447bc14`, `4599f97`, `e6ad193`, `c90c4e9`, `1e66aa2`.

  Earlier branch work is context and was not reviewed again.
- **Spec:** `docs/specs/design-consistency-pass/spec.md`, as amended by D-70 (ADR 0026).
- **Tickets:** `design-consistency-pass-03`, local status `done`, covering AC-60 to AC-64. Work belonging to other tickets:
  - Promotion and AC-81: ticket 04.
  - Restricted execution of the starter: ticket 05.
  - Draft Test Runs: tickets 15 and 16.
- **Fix reports:** `docs/specs/fix-starter-manifest-toml-escaping/report.md`, `docs/specs/fix-draft-conflict-reason/report.md`, `docs/specs/fix-workspace-two-file-rule/report.md`.
- **Sync:** n/a, because the ticket has `external: null`.
- **Date:** 2026-10-17.

## Verdict

**CODE COMPLETE**: all three review axes pass, with no blockers or majors, and all gates are green (300 tests).

Three reviewers checked `1e66aa2` in parallel. Each started with no prior context and none edited files.
- Both majors from the previous review are fixed:
  - Starter Manifest names are now escaped as TOML, not JSON.
  - The FastAPI `Depends` scope rule in `docs/standards.md` is corrected.
- Two of the previous Spec minors are fixed: the conflict log now has a `reason`, and workspace clutter (`.DS_Store`, `.pyc`) no longer breaks saves.
- The remaining findings are minors and do not block.

The coordinating reviewer confirmed two of the new minors by reading the code: the unreachable export handler, and the `.exists()` check that misreports a dangling symlink.

## Findings

No blockers or majors. Minors are grouped by axis. "Carried over" means the finding was in the previous report and is still open.

### Standards

- **[minor] `src/news/service/workspaces.py:91-96,117-118`** (new): export now refuses any code set other than `{main.py}` before it calls `implementation_files`. That call therefore can never raise, and the `except ValidationRejected` handler ("unsafe or conflicting file paths") is dead code.
  - **Source:** baseline §6 (no dead code).
  - **Fix:** build `{MANIFEST: draft.manifest, **draft.code}` directly and drop the handler. Alternatively, fold this into the `implementation_files` split below.
- **[minor] `src/news/service/workspaces.py:142-143`** (new): the Manifest check uses `.exists()`, which follows symlinks. A dangling `manifest.toml` symlink is reported as "missing implementation/manifest.toml" instead of as a rejected link. It is still rejected, so the outcome is safe.
  - **Source:** baseline §5 (failures are handled deliberately and accurately).
  - **Fix:** use `exists() or is_symlink()`, as the `main.py` check on line 147 already does, and add a dangling-link case to the read-failure tests.
- **[minor] `src/news/service/plugins.py:44`** (new): the clause "JSON escaping misses DEL" describes code that has since been removed.
  - **Source:** baseline §1 (comments say why, not history).
  - **Fix:** keep only the first clause.
- **[minor] `src/news/api/app.py:51-61`** (carried over): every route opens a hand-rolled `with transaction(request)`. Its comment no longer has a reason to stand on, because the corrected standard names `Depends(..., scope="function")` as the idiom for this exact case.
  - **Source:** baseline §4, and `docs/standards.md:55`.
  - **Fix:** use `Annotated[Session, Depends(session_dependency, scope="function")]` and keep the `SQLAlchemyError` → 503 mapping.
- **[minor] `src/news/api/app.py:144,156,179`** (carried over): route paths are built by string concatenation (`DRAFTS + "/{draft_id}"`).
  - **Fix:** use `APIRouter(prefix=...)`.
- **[minor] `src/news/service/drafts.py:51-54`** (carried over): a `DraftConflict` is caught only to log it and raise a new one.
  - **Source:** baseline §1.
  - **Fix:** compare inline, or make the pure core a predicate.
- **[minor] `src/news/service/workspaces.py:48-49`** (carried over): the docstring of `implementation_files` says "Select", but the function only validates. The read path no longer calls it, and `save_draft` discards its result.
  - **Fix:** split it into a validator and a Manifest-merge helper.
- **[minor] `src/news/cli/main.py:285`** (carried over): the result of `get_draft(...)` is discarded, and the call's intent (an ownership check) is not stated.
  - **Fix:** add a one-line reason.
- **[minor] `docs/standards.md`** (carried over, stale snapshot):
  - Typer 0.27 and Pydantic 2.14 have no sections.
  - The Alembic section still says "No version-specific rules have been researched yet".
  - The header date (2026-10-16) does not reflect the hand edit to line 55 on 2026-10-17.

  The versions it does cover (Python 3.14, FastAPI 0.143, SQLAlchemy 2.1) match the resolved versions.
  - **Source:** baseline §4.
  - **Fix:** run `/mobua-swe:standards` or `/mobua-swe:setup`.

### Spec

- **[minor] `tests/cli/test_drafts.py:64-101`** (new): `c90c4e9` replaced the file removal in the CLI round-trip with an edit plus clutter files. Removing `main.py` is still tested at the workspace level (`test_removing_main_py_saves_an_empty_code_set`), and saving an empty set is tested at the service level. No test runs the whole sequence: export, unlink `main.py`, save, then confirm through the CLI and the API that `code == {}` was committed.
  - **Source:** the ticket's Verification line: "AC-63: CLI export/edit/save round-trip and API read agree, file removals are saved".
  - **Fix:** add that CLI round-trip.
- **[minor] `tests/cli/test_drafts.py:135`** (carried over): the CLI foreign-Reader parametrization leaves out `list`.
  - **Source:** AC-62.
  - **Fix:** add `"list"`.
- **[minor] `tests/api/test_drafts.py:216-219`** (carried over, optional): the API stdout log test checks only event names and level. The new `reason` field is not asserted on the API path. Exact fields are covered at the service level.
- **[minor] ADR 0026 Consequences and `docs/plugin-drafts.md`** (new): a Draft copied from a legacy multi-file Revision (preserved by D-68, see `test_draft_migration.py:56`) cannot be exported through the CLI. It can only be edited through the API. The ADR mentions only Drafts saved through the API.
  - **Fix:** add one line saying such Drafts are API-only until the Plugin design session.

### Code-complete evidence

- **[minor] `tests/service/test_drafts.py:121`** (carried over): `plugin_draft.parent_rejected` and `plugin_draft.not_found` are checked only by count and level.
  - **Source:** `code-complete.md` item 4.
  - **Fix:** assert the exact event dict.
- **[minor] `src/news/service/drafts.py:96`** (carried over): `plugin_draft.deleted` is logged before the surface commit. No CLI log-file assertion covers it.
  - **Fix:** document the log-before-commit convention, or assert in the CLI commit-failure test.
- **[minor] `docs/specs/design-consistency-pass/evidence/03.md:56,69-78,154-165`** (new): the evidence predates the fixes made after the review.
  - It still describes nested files, "imports include additions and removals", and 290 tests.
  - It names the branch `feat/design-consistency-pass--codex-test`.

  This report and the three fix reports carry the current state.
  - **Fix:** add a short "superseded by" note pointing to the fix reports and D-70.

## Criteria evidence

| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| AC-60 starter | `test_plugin_starter.py::test_new_plugin_has_a_valid_noop_starter` (parses the Manifest; runs `main.py`: exit 0, no output), `::test_blank_name_rejected_without_rows_or_payload_logs`; `test_cli.py::test_plugin_is_created_with_a_valid_starter`; `tests/api/test_drafts.py::test_api_starter_and_draft_crud` | yes | yes: blank and whitespace names | yes: U+001F and U+007F at the edges of the escaped range, U+0080 just past it; 200k-string `tomllib` fuzz run by the reviewer | yes: backslash before `u`, quotes, emoji, newline, U+2028 | yes: `7205191`, `447bc14` | yes |
| AC-60 migration | `test_draft_migration.py::test_upgrade_preserves_legacy_history_without_inventing_ancestry` | yes: whole-database snapshot is equal | n/a: the migration is additive | yes: non-contiguous numbers 1 and 4 | yes: CRLF/Unicode, older current pointer, pinned Binding, downgrade and re-upgrade | yes: `7205191` | yes (SQLite only) |
| AC-61 | `test_drafts.py::test_parent_eligibility_is_same_reader_and_plugin`, `::test_sibling_drafts_copy_an_older_parent_independently`, `::test_bad_targets_insert_nothing_before_rollback`, `::test_unknown_and_foreign_reads_and_lists_are_indistinguishable`; API `test_api_rejects_invalid_parent_targets_without_inserting`, `::test_foreign_and_unknown_api_targets_return_identical_safe_errors` | yes | yes: foreign, wrong Plugin, unknown, Built-in | yes: checked before rollback and from a separate session | yes: sibling Drafts of an older parent | yes: `705a5d8` | yes |
| AC-62 | `test_draft_saves.py::test_unfinished_saves_replace_files_and_preserve_revision_and_binding_state`; CLI `test_cli_export_edit_save_read_matches_api_and_discards_only_saved_draft`; `test_rejected_save_and_delete_preserve_state_before_rollback_and_after_commit`; CLI and API foreign-target tests | yes | yes: scope rejections (CLI `list` missing, minor) | yes: empty file set | yes: invalid TOML, unfinished code, unpinned dependencies | yes: `705a5d8` | yes |
| AC-63 (as amended by D-70) | `test_workspaces.py::test_export_edit_read_and_marker_advance_preserve_exact_text`, `::test_read_ignores_every_file_except_the_manifest_and_main_py`, `::test_removing_main_py_saves_an_empty_code_set`, `::test_export_refuses_drafts_with_files_other_than_main_py`, `::test_read_failures_are_actionable_and_never_return_partial_contents`, `::test_failed_export_leaves_no_partial_destination`; `test_draft_saves.py::test_expected_version_rule`, `::test_stale_saves_even_with_a_cached_draft_leave_state_unchanged_and_log_only_ids`, `::test_competing_saves_allow_one_writer_and_refuse_the_other`; CLI stale, unreadable, commit-failure and marker-write-failure tests | yes | yes: stale save, unreadable files, commit failure | yes: symlinks, directories and FIFOs at `main.py`/the Manifest | yes: CRLF, invalid UTF-8, two threaded writers, `.DS_Store`/`.pyc`/backup clutter. Dangling Manifest symlink untested (minor). Removal not tested through the CLI end to end (minor). | yes: `79483f3`, `c90c4e9` (first-run passes disclosed) | yes |
| AC-64 | `test_draft_saves.py::test_discard_deletes_only_that_draft_and_logs_ids`, `::test_rejected_save_and_delete_preserve_state_before_rollback_and_after_commit[delete-*]`; CLI round-trip; CLI and API foreign `[delete]` | yes | yes | yes: sibling Draft kept | yes: exported files and marker kept | yes: `705a5d8` | yes |

The reviewers read the test code behind every row; none of it was taken from the evidence file on trust.
- **Commit order:** tests always landed in the same commit as the code they cover.
- **Mocks:** the only mocking is `monkeypatch.setenv`.
- **Boundaries:** every boundary has a real integration test:
  - Database: real Alembic on migrated SQLite, a WAL two-thread race, and deferred-constraint COMMIT failures.
  - Filesystem: real temporary directories.
  - CLI: `CliRunner`.
  - API: `TestClient`, plus an OpenAPI contract test.
- **Removed or retargeted tests:**
  - Tests removed in `c90c4e9` covered behaviour that D-70 took away: the read-time path-safety branch and the nested `util.py` round-trip.
  - The symlink and FIFO cases were retargeted to `main.py` and the Manifest.
  - The API code-map path-safety tests are kept.
  - The reasons are recorded in `docs/specs/fix-workspace-two-file-rule/report.md`.

  No test was skipped, marked xfail, or weakened without a stated reason.

## Gates

These are fresh runs at `1e66aa2`:

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors, 0 warnings |
| Lint | `uv run ruff check .` | pass |
| Format | `uv run ruff format --check .` | pass: 157 files formatted |
| Imports | `uv run lint-imports` | pass: 1 contract kept, 0 broken |
| Full suite | `uv run pytest` | pass: 300 tests, 0 skipped, about 6 s |

## Observability delivered

- **Logs:**
  - `info plugin_draft.deleted`: Reader/Plugin/Draft ids. Asserted as an exact dict at the service level, and on API stdout.
  - `info plugin_draft.conflict`: ids, `operation`, expected/actual version, and `reason="stale_version"`, with no payload. This matches spec.md:343. It is asserted:
    - as an exact dict at the service level;
    - in the competing-writers test;
    - by event name and operation in the CLI log file;
    - by event name on API stdout.
  - `plugin_draft.save_rejected`, `plugin_workspace.failed`, `plugin.rejected` and `api.database_failed` are asserted.
  - `plugin_draft.parent_rejected` and `plugin_draft.not_found` are checked by count and level only (minor).
  - The CLI writes JSON lines to its log file, and the API logs to stdout. `hide_parameters=True` keeps saved source out of database error text.
- **Metrics:** none added. This is justified by the spec ("no other metrics in this spec") and D-44.

## Not verified

Code complete is not deployment verified. This review did **not** verify:

- Deployment, runtime behavior in the target environment, or real traffic and data.
- The Draft migration and `UPDATE … RETURNING` on PostgreSQL. All tests run on SQLite; PostgreSQL is ticket 21.
- Restricted execution of the starter (ticket 05), promotion and AC-81 (ticket 04), and Draft Test Runs (tickets 15–16).
- How real macOS Finder and real editors behave inside an exported workspace. Clutter is tested only with synthetic files.

## Deployment verification checklist

Check each item manually or in the observability system to confirm the deployed change does what the spec and ticket intend.

- [ ] **Pre-Draft upgrade:** run `news db upgrade` against a copy of a pre-Draft database that holds representative non-sensitive Plugins, Revisions and Bindings, on both SQLite and PostgreSQL. Diff `plugin`, `plugin_revision` and `channel_binding` before and after.
  - Good: ids, numbers, contents, current pointers and Bindings are identical.
  - Good: every `parent_revision_id` is NULL.
  - Good: there are no `plugin_draft` rows and no synthetic starter Revisions.
- [ ] **Starter:** create a Reader Plugin through the CLI and through the API, using a name with quotes, a backslash and an emoji.
  - Good: Revision 1 is current.
  - Good: its Manifest parses with `tomllib` and keeps the name exactly.
- [ ] **Unfinished Draft save:** export a Draft, put invalid TOML in `manifest.toml`, then delete `main.py` and save.
  - Good: CLI read and list agree with API GET, and `code` is empty.
  - Good: no new Revision is created, and no current pointer or Binding changes.
- [ ] **macOS clutter:** open the exported `implementation/` folder in Finder (which creates `.DS_Store`), and run `main.py` locally (which creates `__pycache__`). Edit `main.py` with an editor that writes backup files, then save.
  - Good: the save succeeds, and only `manifest.toml` and `main.py` are stored.
- [ ] **Stale save:** export a Draft, update the same Draft through the API, then save the stale workspace from the CLI.
  - Good: the CLI reports a conflict.
  - Good: the stored contents and the local marker are unchanged.
  - Good: the CLI log file has `plugin_draft.conflict` with ids, `operation="save"`, expected/actual version and `reason="stale_version"`, and no source.
- [ ] **Discard:** delete the Draft.
  - Good: a sibling Draft, all Revisions, all Bindings and the local exported files remain.
  - Good: server stdout or the CLI log has `plugin_draft.deleted` with Reader/Plugin/Draft ids only.
- [ ] **Log inspection:** search the CLI JSON logs and server stdout for a sentinel string placed in Draft code or config.
  - Good: the sentinel never appears.
