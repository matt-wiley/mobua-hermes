# Fix report: Draft conflict log reason

- **Covers:** the fix commit after `4599f97` on branch `feat/design-consistency-pass`.
- **Source:** minor Spec finding in `docs/specs/design-consistency-pass/report.md` (ticket `design-consistency-pass-03`).
- **Date:** 2026-10-17.

## Reproduction (criterion)

- **Expected:** spec.md:343 says "`info` `plugin_draft.conflict`: Reader/Plugin/Draft ids, operation, expected/actual version or current-selection ids, safe reason."
- **Actual:** the event carried the ids, `operation`, and the expected/actual versions, but no reason.
- **Root cause:** `_conflict` in `src/news/service/drafts.py` never set a reason field.
- **Fix:** `_conflict` now logs `reason="stale_version"`. It is the only reason either save conflict path can produce: the up-front version check and the conditional `UPDATE` that catches a competing writer. Both mean the stored version moved past the caller's expected version.

## Evidence

| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| `plugin_draft.conflict` carries a safe reason | `tests/service/test_draft_saves.py::test_stale_saves_even_with_a_cached_draft_leave_state_unchanged_and_log_only_ids` (exact event dict); `::test_competing_saves_allow_one_writer_and_refuse_the_other` (exactly one conflict event, `reason="stale_version"`, expected version 1) | n/a: logging on the failure path only | yes: stale save with a cached Draft | yes: the competing-writer `UPDATE` path, two threads | n/a: one reason code | yes | yes |

**Red** (both tests before the fix):

```
E   AssertionError: ... {'operation': 'save', 'expected_version': 1, 'actual_version': 2, ...} != {..., 'reason': 'stale_version'}
E   KeyError: 'reason'
2 failed, 15 passed
```

**Green:** 49 passed across the service, CLI, and API Draft test files.

## Gates

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass: 154 files formatted, 1 contract kept |
| Full suite | `uv run pytest` | pass: 293 tests |

## Observability added

`reason="stale_version"` on `info plugin_draft.conflict`. It is a fixed code, so it can't carry source code, config, or credentials. Ticket 04 adds promotion conflicts and their "current-selection ids". It should add its own reason codes there.

## Not verified

- Deployment, and the conflict line in deployed CLI log files or server stdout.

## Deployment verification checklist

- [ ] Export a Draft, update it through the API, then save the stale workspace from the CLI. The CLI log file (or server stdout, for an API save) has `plugin_draft.conflict` with `operation="save"`, the expected and actual versions, and `reason="stale_version"`, with no source text.
