# Code-complete report: review-followups-01-01, CLI writes its logs to a file

- **Covers:** `945315f..766f589` on branch `feat/design-consistency-pass`
- **Spec:** `docs/specs/review-followups-01/spec.md`
- **Tickets:** review-followups-01-01 (done). Tickets 02–06 are open and are **not** covered by this report.
- **Sync:** n/a (no `external:` links)
- **Date:** 2026-10-17

## Verdict
**CODE COMPLETE** (ticket 01-01 only): AC-9, AC-10, AC-11 and AC-14 are met by tests that assert them, all three axes pass, and the gates are green. All findings are minor.

The spec as a whole is not code complete until tickets 02–06 are done and reviewed.

## Findings
There are no blockers or majors. The minor findings are listed below.

### Standards
- [minor] `src/news/cli/main.py:56-75`: baseline §5 and spec D-6 ("fails fast before any work"). The group callback runs before a subcommand's `--help` is parsed. So `news db upgrade --help` creates the log directory and file, and with an unopenable path, `--help` exits 1. This was reproduced with `NEWS_CLI_LOG_FILE=/dev/null/x news db upgrade --help`, and shell completion is affected the same way. Fix: return early from `main` when `ctx.resilient_parsing` is set, and decide whether `--help` should open the log at all.
- [minor] `src/news/cli/main.py:52`: baseline §4 (use the existing idiom). The default is written into the `help` text by hand. Fix: use `show_default="$XDG_STATE_HOME/news/cli.log"`.
- [minor] `docs/mobua-swe.md:11-13`: repo config vs D-6. The `observability.logging` entry still says "JSON to stdout", and `where_to_look` doesn't mention the CLI log file. The `commands_verified` comment says 53 tests; there are now 70. Fix: update it in a separate change, or re-run `/mobua-swe:setup`.
- [minor] `docs/standards.md` snapshot: baseline §4. Typer 0.27 and structlog 26.1 are direct dependencies with no standards library entry. Fix: add `typer` and `structlog` entries, then re-run `/mobua-swe:setup`. The snapshot is not stale: it was taken 2026-10-16 and matches `uv.lock`, and the hold on Python 3.14 is documented.

### Spec
- [minor] `src/news/cli/main.py:70`: D-6 says the message "names the path, the OS error and the override". `error.strerror` can be `None` for an OSError with no errno, which would print "None". Fix: `error.strerror or str(error)`.
- [minor] `src/news/cli/log_file.py:10-13`: AC-9 says "With neither set, they go to `$XDG_STATE_HOME/news/cli.log`". The resolver also ignores an empty or relative `XDG_STATE_HOME`. This follows the XDG Base Directory spec, but the spec doesn't record it. Fix: add a line to D-6.
- [minor, pre-existing, not this diff] Nothing in `src/` outside the CLI calls `configure_logging()`, so the server process never configures structlog. The deployment check "`docker logs`: server JSON lines on stdout, as before" depends on the server doing that. Fix: confirm or add server logging setup, likely with the container work.

### Code-complete evidence
- [minor] `tests/cli/test_cli.py:332-354` (`read_only_dir`): ticket Seams, and the spec checklist line "As root, permissions don't block". Nothing protects this test when it runs as root, so in a root CI container it fails instead of skipping. Fix: `pytest.mark.skipif(os.geteuid() == 0, ...)`.
- [minor] `tests/cli/test_cli.py:345-354`: the ticket says "Assert the database file was not created **or changed**". Only "not created" is tested. Fix: add a case against an existing database whose bytes stay unchanged, or justify in the evidence why "not created" is enough.
- [minor] `tests/cli/test_cli.py:357-370` (`test_a_log_file_path_that_is_a_directory_is_reported`): AC-11 is under-asserted. The test doesn't check the OS error text, the override names, or empty stdout. Fix: add those three assertions.
- [minor] `tests/cli/test_cli.py:290-320` (the XDG default and `~/.local/state` fallback tests): neither checks `exit_code` or stdout. Fix: assert both.
- [minor] An empty `NEWS_CLI_LOG_FILE=""` is untested. A manual run shows it falls back to the XDG path. Fix: pin that with a CLI test.
- [minor] `docs/specs/review-followups-01/evidence/01.md`: the evidence names the deployment checks the ticket feeds, but lists none. This report's checklist fills that gap.

## Criteria evidence
| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| AC-9 | `test_log_file.py`: 6 resolver tests. `test_cli.py`: `test_the_log_file_option_wins_over_the_environment`, `test_log_lines_go_to_the_file_named_by_the_environment_and_stdout_has_none`, `test_logs_default_to_the_xdg_state_directory`, `test_logs_fall_back_to_local_state_under_home_without_xdg_state_home` | yes | under AC-11 (justified) | yes: empty or relative XDG, relative explicit path. Empty env var is untested (minor). | yes: a missing directory is created in every CLI case | yes | yes |
| AC-10 | `test_logs_go_to_the_given_stream_and_not_stdout`, `test_log_lines_go_to_the_file_named_by_the_environment_and_stdout_has_none`, `test_a_second_command_appends_to_the_log_file`; `created_id` reads the whole of stdout | yes | n/a: write-after-open failure is out of scope (justified) | yes: `stdout == ""` | yes: a second run appends and keeps the first line | yes | yes |
| AC-11 | `test_an_unopenable_log_file_fails_before_touching_the_database`, `test_a_log_file_path_that_is_a_directory_is_reported` | via AC-9/10 | yes: EACCES and EISDIR | partly: "database not changed" is untested (minor) | root run unguarded (minor) | yes | yes |
| AC-14 | `test_logs_are_json_lines_on_stdout` (unchanged) | yes | n/a (justified) | n/a (justified) | stream variant under AC-10 | n/a: regression guard (justified) | yes |

From commit history: tests landed in the same commits as their code (6b3a269, 9fa25af, 3e5db56), and no production code came first. The red-first runs are recorded in `evidence/01.md`. No tests were deleted, weakened or skipped. The only change to an existing assertion, `created_id`, is stricter.

## Gates
| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass (0 errors) |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass (1 import contract kept) |
| Full suite | `uv run pytest` | pass (70 tests, none skipped) |

## Observability delivered
- **Logs:** the CLI appends structlog JSON lines to `--log-file` / `NEWS_CLI_LOG_FILE`. The default is `$XDG_STATE_HOME/news/cli.log`, else `~/.local/state/news/cli.log`. `configure_logging()` still defaults to stdout for the server. An unopenable log file is reported on stderr with the path, the OS error and both overrides, because it can't be logged to the file that failed to open. That message is tested. The `docs/standards.md` logging line now matches D-6.
- **Metrics:** none, as the spec requires. These are low-volume CLI events and the logs already cover them.

## Not verified
Code complete is not deployment verified. This review did **not** verify:
- Deployment, runtime behaviour in the target environment, or real traffic and data.
- A run as root, or in a container. The read-only-directory test assumes a non-root user.
- That the server process emits JSON on stdout at all. No server code calls `configure_logging()` (see Spec findings).
- That `NEWS_CLI_LOG_FILE` is set in the container image. That belongs to the container ticket.
- Anything in tickets 02–06.

## Deployment verification checklist
Evaluate manually or in the observability system to confirm the deployed change matches the intent of the spec or ticket.

- [ ] **Clean venv, non-root:** `NEWS_CLI_LOG_FILE=/tmp/news-ok/cli.log news --database-url sqlite:///x.db db upgrade`. Expect exit 0, `/tmp/news-ok/` created, and stdout carrying only command output.
- [ ] **Invalid bind:** run `news channel bind … --config '{}'`. Expect stdout to be empty, and `tail -1 /tmp/news-ok/cli.log | jq '.event,.level,.timestamp'` to show `channel_revision.rejected`, `info` and a timestamp. Run it again and expect `wc -l` to go up by 1.
- [ ] **Default location:** with `NEWS_CLI_LOG_FILE` and `XDG_STATE_HOME` both unset, any logging command creates `~/.local/state/news/cli.log`.
- [ ] **Unopenable log file, non-root:** `mkdir -m 500 /tmp/ro && NEWS_CLI_LOG_FILE=/tmp/ro/logs/cli.log news --database-url sqlite:///y.db reader create A`. Expect exit 1, and one stderr line naming the path, `Permission denied`, `--log-file` and `NEWS_CLI_LOG_FILE`. Expect no `y.db`. Repeat against an existing database: its checksum should not change. As root, use a read-only mount.
- [ ] **`docker logs <container>`:** server JSON lines on stdout, as before.
- [ ] **Container, after the container ticket sets `NEWS_CLI_LOG_FILE=/data/logs/cli.log`:** CLI logs persist on the data volume across restarts.
