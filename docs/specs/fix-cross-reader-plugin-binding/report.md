# Fix report: cross-Reader Plugin Revision binding

- **Covers:** `b139d48..d664747` on branch `feat/design-consistency-pass`
- **Source:** major finding in `docs/specs/design-consistency-pass/report.md` (Standards and Code-complete evidence axes)
- **Date:** 2026-10-17

## Verdict
**FIXED, pending independent review.** Saving a Channel Revision now accepts only Plugin Revisions owned by the acting Reader, or Built-in ones.

## Reproduction (the criterion)
- **Expected:** when Reader B saves a Channel Revision with a Binding to Reader A's Plugin Revision, the save is rejected with `bindings.0.plugin_revision_id: no such Plugin Revision`, no Channel Revision is created, and the rejection is logged. (ADR 0018: "A Binding may only reference Revisions of Plugins owned by the Channel's Reader, or of Built-in Plugins"; docs/standards.md: "Scope every row by Reader … in the service layer".)
- **Actual (before):** the save succeeded and created Channel Revision 2. With an invalid config, the errors also revealed Reader A's config schema (`bindings.0.url`).

## Root cause
`_binding_errors` in `src/news/service/channels.py` loaded the Plugin Revision by primary key with `session.get`. The Reader scope that `_get_channel` applies to Channels never reached Plugin Revisions.

## Fix
`_binding_errors` takes the acting Reader's id and selects the Plugin Revision only if its `reader_id` is that Reader's id or `NULL` (Built-in, ADR 0019). Any other Plugin Revision is reported exactly as a missing one, so the error reveals nothing about it. Only one private helper in one source file changed. There is no migration, config, or dependency change.

This is the single service-layer eligibility rule that D-4 requires. Ticket 05 (AC-4) should extend this rule rather than add a second one.

## Evidence
| Test | Category | Red (before fix) | Green |
|---|---|---|---|
| `test_binding_another_readers_plugin_revision_is_rejected_as_unknown` | failure mode, plus the log and no-Revision checks (counted before any rollback) | `Failed: DID NOT RAISE ChannelRevisionRejected` | pass |
| `test_another_readers_plugin_revision_does_not_reveal_its_schema` | edge: information leak | `assert ['bindings.0.url'] == ['bindings.0.plugin_revision_id']` | pass |
| `test_built_in_plugin_revision_can_be_bound_by_any_reader` | boundary: `reader_id IS NULL` stays bindable | n/a: already passing; a guard against an over-tight fix | pass |

The test helper `a_built_in_plugin_revision` (in `tests/service/factories.py`) inserts a system-owned row directly, because seeding is ticket 05.

## Gates
| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass (0 errors) |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass (1 contract kept) |
| Full suite | `uv run pytest` | pass (56 tests) |

## Observability added
None new. The rejection goes through the existing `info channel_revision.rejected` event (Channel id and errors), which the reproduction test asserts.

## Not verified
- Deployment, or behavior in the container image.
- Postgres. The `IS NULL` / `OR` query is portable, but it ran on SQLite only.
- That the other review findings are resolved. They are untouched and routed to `/mobua-swe:grill`.

## Deployment verification checklist
- [ ] Create Readers A and B. Run `news plugin create --reader <A> …`, then `news channel create --reader <B> Local`, then `news channel bind --reader <B> --channel <B's channel> --plugin-revision <A's revision> --config '{"url":"https://x"}'`. Expect exit 1 with `bindings.0.plugin_revision_id: no such Plugin Revision` on stderr.
- [ ] After that attempt, `SELECT count(*) FROM channel_revision WHERE channel_id = '<B's channel>'` is still 1.
- [ ] `docker logs <container>` (or the CLI's stdout) shows a `channel_revision.rejected` line with B's `channel_id` and the `plugin_revision_id` error.
- [ ] Binding B's own Plugin Revision to the same Channel still prints "Saved Channel Revision 2.".
