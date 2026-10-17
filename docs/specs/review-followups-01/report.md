# Code-complete report: review-followups-01-03, error types, service failure logging, and the Reader check

- **Covers:** `01e4f81..ea17703` on branch `feat/design-consistency-pass`
- **Spec:** `docs/specs/review-followups-01/spec.md`
- **Tickets:** review-followups-01-03 (done). Ticket 01 was reviewed earlier: its report is at `01e4f81:docs/specs/review-followups-01/report.md`. Tickets 02, 04, 05 and 06 are open and are **not** covered by this report.
- **Sync:** n/a (no `external:` links)
- **Date:** 2026-10-17

## Verdict
**CODE COMPLETE** (ticket 01-03 only): tests assert AC-15, AC-16, AC-17 and AC-19, the D-13 checks hold, all three axes pass, and the gates are green. All findings are minor.

The spec as a whole is not code complete until tickets 02 and 04–06 are done and reviewed.

## Findings
There are no blockers or majors. The minor findings are listed below.

### Standards
- [minor] `src/news/service/binding_config.py:39`: baseline §1 (comments say why). The D-13 comment sits above `_missing_fields`, but it also explains the `cast(dict[str, Any], error.instance)` in `_unexpected_fields`. It also partly repeats the comment at lines 26-27. Fix: say in the comment that it covers both helpers. That keeps the ticket's "one comment" rule.
- [minor] `src/news/service/validation.py:19` and `src/news/cli/main.py:87`: baseline §1 and §4 (no duplicated logic). `error.field or '(root)'` is formatted in two places, so the CLI output and the exception message could drift apart. Fix: in ticket 02 (spec D-10), have `_fail` reuse the base class's formatting. The evidence already defers it there.
- [minor, adjacent, pre-existing] `src/news/service/channels.py:63-67`: baseline Observability. `channel_revision.rejected` logs `channel_id` and `errors` but not `reader_id`. The new events all include `reader_id`, so the rejection events are now inconsistent. This is out of scope for this ticket. Fix: open a follow-up.
- Standards snapshot: not stale. `docs/standards.md` (2026-10-16) matches `docs/mobua-swe.md` and `uv.lock`. As the ticket 01 report already noted, structlog 26.1, Typer 0.27 and jsonschema 4.26 have no library entries. Fix: add them the next time `/mobua-swe:setup` runs.

### Spec
- [minor] `src/news/service/validation.py:19`: spec AC-19, "Each has the message `"<field>: <message>"`, joined with `"; "`". The ticket's Verification asks for "an empty `field` shown at the root", and the code does that: `str(exception)` now renders `(root)` where it used to render `": <message>"`. The spec's AC-19 doesn't mention `(root)`, so the spec and the ticket disagree. The evidence discloses the change, and it is tested. Fix: add the `(root)` rule to AC-19. No code change.
- [minor] `src/news/service/plugins.py:28`: spec D-7, "the service layer logs rejected user input at `info`, where the rejection is raised". `PluginRevisionRejected` is raised in the pure `parse_manifest`, but `create_plugin` catches it, logs it and re-raises it, because only `create_plugin` has the `reader_id`. This is justified and recorded in the evidence. Fix: none needed. Optionally, note this placement in D-7.

### Code-complete evidence
- [minor] `tests/cli/test_cli.py:379-413`: an evidence gap for the deployment check "CLI, unknown Reader … The log file has `reader.not_found`". The two CLI unknown-Reader tests check the exit code, stderr, empty stdout and `SystemExit`. They don't check that `reader.not_found` reaches the CLI log file. Fix: assert `[line["event"] for line in log_lines(log_file)] == ["reader.not_found"]`, here or in ticket 02.
- [minor] `docs/specs/review-followups-01/evidence/03.md:84-91`: code-complete item 2 (red for the right reason). Two of the four AC-17 service red failures are `NotImplementedError` from the stub. That is weaker than an assertion failure. The `IntegrityError` failures do show the missing check, so this is acceptable. Fix: none. Next time, a no-op stub would show that rows were written.

## Criteria evidence
| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| AC-15 | `test_plugins.py`: `test_rejected_manifest_is_logged_with_the_reader_and_errors`, `test_malformed_manifest_is_logged_with_its_root_error`, `test_plugin_with_an_invalid_manifest_is_rejected_and_not_saved` | yes: the existing create tests log nothing | yes: schema rejection and TOML parse failure | yes: timeout boundaries in `test_manifest.py` | yes: root-level error | yes | yes |
| AC-16 | `test_channels.py`: `test_an_unknown_channel_is_not_found_and_logged`, `test_another_readers_channel_is_not_found_and_logged`, `test_another_readers_channel_cannot_be_revised`. `test_cli.py`: `test_binding_to_an_unknown_channel_is_reported` | yes: a found Channel logs nothing (asserted exactly) | yes: both not-found paths, both through `_get_channel` | n/a: no range to bound (justified) | n/a (justified) | yes | yes |
| AC-17 | `test_readers.py`: 5 tests. `test_cli.py`: `test_creating_a_{channel,plugin}_for_an_unknown_reader_is_reported_without_a_traceback` | yes | yes: in the service and in both CLI commands | yes: `not session.new` and row counts are 0 | n/a: Typer rejects malformed UUIDs (justified) | yes (2 of 4 service reds are stub `NotImplementedError`, minor) | yes |
| AC-19 | `test_validation.py`: 8 tests. The renamed tests in `test_binding_config.py`, `test_manifest.py`, `test_channels.py` and `test_plugins.py`. A grep finds no `ConfigError` or `ManifestError` | yes | n/a: value types with no failure path (justified) | yes: one error, zero errors | yes: an empty field shown as `(root)` | yes | yes |
| D-13 | Checked in review: `cli/main.py:98` uses `cast` with no ignore, and `binding_config.py:39` has the comment. The only remaining `pyright: ignore` is the commented `iter_errors` one | n/a | n/a | n/a | n/a | n/a: refactor covered by the existing `_parse_config` tests | yes |

From commit history: each test landed in the same commit as its code (b8ed188, 349f097, 3bc04fb, de53202). b032859 is a refactor covered by the existing tests. No tests were deleted, weakened or skipped. The changes to `tests/` are renames and additions only. There are no mocks: the service tests run on migrated SQLite, and the CLI tests use `CliRunner` against a real database.

## Gates
| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass (0 errors) |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass (1 import contract kept) |
| Full suite | `uv run pytest` | pass (89 tests, none skipped) |

## Observability delivered
- **Logs:** all three are structlog events at `info` from the service layer, and each is asserted exactly with `capture_logs`.
  - `reader.not_found` (`reader_id`): `service/readers.py:28`.
  - `channel.not_found` (`reader_id`, `channel_id`): `service/channels.py:118`.
  - `plugin_revision.rejected` (`reader_id`, `errors` as field/message pairs): `service/plugins.py:28`.

  From the CLI, they go to the CLI log file that ticket 01 set up.
- **Metrics:** none, as the spec requires (D-15).

## Not verified
Code complete is not deployment verified. This review did **not** verify:
- Deployment, runtime behavior in the target environment, or real traffic and data.
- The installed `news` binary on a real terminal. In particular, that no traceback appears outside `CliRunner`.
- That the three events reach the real CLI log file. No test checks the file for `reader.not_found` (see findings).
- Server-side emission of these events. No server code calls `configure_logging()` (from the ticket 01 report).
- The final CLI stderr shape with `Logged to <path>.`, which belongs to ticket 02.
- Anything in tickets 02 and 04–06.

## Deployment verification checklist
Check these by hand or in the observability system, to confirm the deployed change does what the spec and ticket intend.

- [ ] **CLI, unknown Reader:** run `news channel create --reader <random uuid> X` and `news plugin create --reader <random uuid> --manifest m.toml --code main.py`. Each should print `no Reader <id>` and exit 1, with no traceback. `tail -1 <cli.log> | jq '.event,.level,.reader_id'` should show `reader.not_found`, `info` and the id. No `channel` or `plugin` row should be added. After ticket 02, stderr also shows `Logged to <path>.`
- [ ] **CLI, invalid Manifest:** run `news plugin create --reader <id> --manifest bad.toml --code main.py` with a Manifest whose timeout is 0. It should exit 1 with the field error. The log file should have `plugin_revision.rejected` with `reader_id` and `errors`. The `plugin` and `plugin_revision` counts should not change.
- [ ] **CLI, unknown or another Reader's Channel:** run `news channel bind --reader <id> --channel <id> --plugin-revision <id> --config '{}'` with a random Channel id, and again with another Reader's Channel. Each should exit 1, and the log file should have `channel.not_found` with `reader_id` and `channel_id`. The other Reader's Channel should get no new Revision.
