---
id: review-followups-01-01
title: CLI writes its logs to a file
status: done
blocked_by: []
external: null
---

# CLI writes its logs to a file

## Goal
`news` commands send service-layer logs to a JSON-lines file chosen by `--log-file` / `NEWS_CLI_LOG_FILE`, defaulting to the XDG state directory. They fail fast when that file can't be opened, and stdout carries only command output. The server's `configure_logging()` default (JSON on stdout) is unchanged.

## Criteria covered
AC-9, AC-10, AC-11, AC-14

## Seams
- **Pure core:** log path resolution, a function of `(explicit option or env value, XDG_STATE_HOME, home dir)` that returns a `Path`. Unit-test it with explicit values, not the real environment.
- **Edge:** `configure_logging(stream)` (or an equivalent parameter) and the CLI callback that opens the file in append mode, creating its directory. Test through Typer's `CliRunner`, with `NEWS_CLI_LOG_FILE` and `XDG_STATE_HOME` pointing into `tmp_path`.
- **Unopenable file:** a path under a read-only directory created in `tmp_path`. Assert the database file was not created or changed.

## Observability
- Destination split (spec D-6): the server writes to stdout and the CLI to its log file. Update the logging line in `docs/standards.md` (Repo overrides) to the D-6 wording.

## Verification
- **AC-9:** explicit option wins over the env var, which wins over `XDG_STATE_HOME`, which wins over `~/.local/state`. A missing directory is created.
- **AC-10:**
  - every line in the file parses as JSON with `event`, `level` and `timestamp`;
  - two commands produce appended lines, with the first kept;
  - a command that logs `channel_revision.rejected` leaves stdout empty;
  - existing CLI tests stop relying on "last stdout line" and read the whole of stdout.
- **AC-11:** exit 1. stderr names the path, the OS error text, `--log-file` and `NEWS_CLI_LOG_FILE`. No database file is created.
- **AC-14:** the existing `test_logs_are_json_lines_on_stdout` still passes unchanged.
- **Feeds deployment checks:**
  - "CLI, unopenable log file";
  - "`docker logs`: server JSON lines on stdout, as before";
  - the container check, which needs the container ticket to set the variable.

## Out of scope
- The `Logged to <path>.` pointer, the top-level exception handler, and echo-after-commit (ticket 02).
- New log events (ticket 03).
- Log rotation.
- Setting the variable in the container image.
