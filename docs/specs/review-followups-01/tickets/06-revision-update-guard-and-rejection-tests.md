---
id: review-followups-01-06
title: Revision update guard and stronger rejection tests
status: done
blocked_by: [review-followups-01-03]
external: null
---

# Revision update guard and stronger rejection tests

## Goal
A service-layer `before_flush` listener raises `ImmutableRevisionError` when a Plugin Revision, Channel Revision or Plugin Binding has changed attributes. Inserts, and moves of the current-Revision pointer, still work. The Channel Revision rejection tests assert what the save left behind before any rollback.

## Criteria covered
AC-4, AC-5, AC-20

## Seams
- **Edge:** the session event listener, registered in the service layer so every session the CLI or API opens is guarded. Test it on a real migrated SQLite session.
- **AC-20:** checks the session state (`session.new`, the current-Revision pointer) right after `ChannelRevisionRejected`, plus the Revision count from a second connection.

## Observability
- None new. `ImmutableRevisionError` signals a programming error. It propagates, and the CLI's top-level handler logs it, once ticket 02 lands.

## Verification
- **AC-4:** one case per guarded class: change an attribute on a committed row, flush, and expect `ImmutableRevisionError` naming the table and the attribute. After a rollback, the stored row is unchanged. In-place mutation of a JSON column isn't change-tracked, so it doesn't reach the guard; record that as a known limit in the evidence.
- **AC-5:**
  - `create_channel` and `bind_plugin` still succeed;
  - the Channel's and the Plugin's current-Revision pointers can be moved to an existing Revision;
  - deleting a Revision row is not blocked (a non-goal check, so the guard stays narrow).
- **AC-20:** the existing missing-field and one-invalid-binding service tests, and the CLI invalid-bind test, assert their checks before any rollback. The CLI test reads through a separate engine.

## Out of scope
- Guarding deletes.
- Database triggers.
- The draft table (plugin-drafts spec).
