# Fix report: Workspace reads only the Manifest and main.py

- **Covers:** the fix commit after `e6ad193` on branch `feat/design-consistency-pass`.
- **Source:** minor Spec finding in `docs/specs/design-consistency-pass/report.md` (ticket `design-consistency-pass-03`): a workspace save fails on `.DS_Store`/`.pyc` and saves editor backups as Plugin code.
- **Decision:** the user set an interim rule until a Plugin design session: a Plugin is two files, a Manifest and one Python file. It was applied to the workspace only. Storage, the service, and the API still accept a map of code paths. This narrows `docs/plugin-drafts.md`'s "complete code-file set" for CLI workspaces, which are now documented there as interim.
- **Date:** 2026-10-17.

## Reproduction (criterion)

- **Expected:** saving an exported workspace succeeds when the folder also contains local clutter (`.DS_Store`, `__pycache__/*.pyc`, `main.py~`, `.swp`, other files). Only the Manifest and `main.py` are saved.
- **Actual:** `_read_files` imported every file under `implementation/` as UTF-8 Plugin code. A binary `.DS_Store` failed every save with "cannot read all UTF-8 files", and text clutter was saved as Plugin code.
- **Root cause:** the workspace defined the Plugin as "every file in the folder", so any file the OS or editor left behind became part of the Plugin.
- **Fix:** `src/news/service/workspaces.py` now works as follows:
  - `read_workspace` reads exactly `manifest.toml` and `main.py` (constant `CODE`). A missing `main.py` saves an empty code set.
  - `export_workspace` refuses a Draft whose saved code has any other file, so it never drops them silently.
  - The recursive `_read_files` is replaced by `_read_text`.
  - The no-longer-reachable `ValidationRejected` read branch is removed.

## Evidence

| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| Save reads only the Manifest and `main.py` | `tests/service/test_workspaces.py::test_read_ignores_every_file_except_the_manifest_and_main_py`; `tests/cli/test_drafts.py::test_cli_export_edit_save_read_matches_api_and_discards_only_saved_draft` (`.DS_Store` and `new.py` beside an edited `main.py`) | yes | n/a | yes: `__pycache__/` directory, a symlink, and a FIFO beside the two files are ignored | yes: binary `.DS_Store`/`.pyc`/`.swp`, `main.py~`, `helper.py` | yes | yes |
| Export holds exactly two files, with text preserved | `::test_export_edit_read_and_marker_advance_preserve_exact_text` | yes | n/a | yes: exactly `main.py` and `manifest.toml` | yes: CRLF, non-ASCII | yes | yes |
| Removal is still saved | `::test_removing_main_py_saves_an_empty_code_set` | yes | n/a | yes: empty code set | n/a | passed on first run (the old reader also handled this); kept as a guard | yes |
| Export never drops files | `::test_export_refuses_drafts_with_files_other_than_main_py` (extra file, nested `lib/main.py`, other name) | n/a | yes: actionable error, no destination, `plugin_workspace.failed` logged, file names not echoed | yes: nested path | yes | yes | yes |
| The two files must be regular files | `::test_read_failures_are_actionable_and_never_return_partial_contents` with `symlink_main`, `symlink_manifest`, `symlink_implementation`, `fifo_main`, `main_is_directory` (plus the existing marker, UTF-8, and permission cases) | n/a | yes | yes | yes: `main_is_directory` was silently read as an empty set before the fix | yes: `main_is_directory` | yes |

**Red** (before the fix):

```
FAILED test_read_ignores_every_file_except_the_manifest_and_main_py
  OSError: symbolic links are not workspace files -> WorkspaceError: cannot read all UTF-8 files
FAILED test_export_refuses_drafts_with_files_other_than_main_py[code0..2]   Failed: DID NOT RAISE WorkspaceError
FAILED test_read_failures_...[main_is_directory]                            Failed: DID NOT RAISE WorkspaceError
FAILED test_cli_export_edit_save_read_matches_api_and_discards_only_saved_draft
  Cannot read workspace ...: cannot read all UTF-8 files (exit code 1)
```

The first run also failed `test_export_edit_read_and_marker_advance_preserve_exact_text`, because of an ordering mistake in the new test itself (the `sorted()` order). It was corrected before the fix.

**Changed tests (justified):**
- The read-failure cases `symlink_file`, `symlink_dir`, and `fifo` were extra files beside `main.py`. Under the rule those are now ignored, which `test_read_ignores_every_file_except_the_manifest_and_main_py` asserts. They were retargeted at the two files themselves and at `implementation/`.
- The round-trip test no longer uses a nested `util.py`, because nested files are outside the workspace rule. Path-safety tests for the API's code map are unchanged.

## Gates

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass: 1 contract kept |
| Full suite | `uv run pytest` | pass: 300 tests |

## Observability added

There is no new event. Export's new refusal uses the existing `info plugin_workspace.failed` (operation `export`, fixed reason, no file names), which the new test asserts. Ignored files are not logged: they are expected local clutter, and logging their names would leak folder contents.

## Not verified

- Deployment, and real Finder or editor behaviour inside an exported folder on macOS.
- The final Plugin file model. That is left to the Plugin design session, and this rule is interim.

## Deployment verification checklist

- [ ] On macOS, export a Draft with `news plugin draft export`, open `implementation/` in Finder (which creates `.DS_Store`), and run `main.py` once with `python` (which creates `__pycache__/`). Edit `main.py`, then run `news plugin draft save`. It succeeds, and `news plugin draft read` shows only `main.py` in `code`.
- [ ] Save a Draft through the API with `{"code": {"main.py": "...", "helper.py": "..."}}`, then export it from the CLI. Export fails with "saved code has files other than main.py", no destination directory is created, and the CLI log has `plugin_workspace.failed` with `operation="export"`.
