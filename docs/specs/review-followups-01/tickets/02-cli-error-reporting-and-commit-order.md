---
id: review-followups-01-02
title: CLI error reporting and echo after commit
status: done
blocked_by: [review-followups-01-01, review-followups-01-03]
external: null
---

# CLI error reporting and echo after commit

## Goal
Every CLI failure ends with a short stderr message pointing to the log file. Expected failures show their specific message plus `Logged to <path>.`. Unexpected exceptions go through one top-level handler that logs the traceback to the file. Commands print results only after their transaction has committed.

## Criteria covered
AC-12, AC-13, AC-18

## Seams
- **Edge:** the CLI's transaction helper and a top-level handler around command execution. `ValidationRejected` and the `LookupError` subclasses (`ChannelNotFound`, `ReaderNotFound`, from ticket 03) are handled in one place.
- **Commit failure:** a trigger, added to the test database from a real second SQLite connection, writes a dangling `DEFERRABLE INITIALLY DEFERRED` foreign key whenever the command inserts. SQLite checks deferred keys only at COMMIT, so the command's flush succeeds and its commit fails. No mocks. (Amended in review: a held write lock fails the first INSERT at flush, never at commit.)
- **Flush failure:** a real second SQLite connection holding `BEGIN IMMEDIATE`, so the command's first INSERT fails with a lock error. No mocks.

## Observability
- `error` `cli.unexpected_error`: `command`, `exc_info`. Written to the CLI log file. Not written when the failure comes before the log path is known; stderr then ends `No log file was open to record it.` `command` names only the commands resolved so far.

## Verification
- **AC-12:**
  - **Rejected bind:** the field error, then `Logged to <path>.`, exit 1.
  - **Unknown Channel:** `no Channel …`, then the pointer.
  - **Unknown Reader:** `no Reader <id>`, then the pointer.
- **AC-13:** using the flush-failure setup:
  - the log file has `cli.unexpected_error` with `command` and a traceback;
  - stderr is exactly one line in the specified format, with no `Traceback` text;
  - exit 1.
- **AC-18:** using the commit-failure setup, for each writing command:
  - stdout is empty;
  - exit 1;
  - a fresh connection finds none of the command's rows (for example no new Reader);
  - with the flush-failure setup as well, counting only after the lock is released.
- **Feeds deployment checks:** "CLI, invalid bind" and "CLI, unknown Reader".

## Out of scope
- Where the log file lives and how it is opened (ticket 01).
- Raising and logging `ReaderNotFound`, `channel.not_found` and `plugin_revision.rejected` in the service (ticket 03).
- API error handling.
