---
id: review-followups-01-03
title: Error types, service failure logging, and the Reader check
status: todo
blocked_by: []
external: null
---

# Error types, service failure logging, and the Reader check

## Goal
Rename the validation error types:
- `ConfigError` becomes `FieldError`, under a `ValidationRejected` base;
- `ManifestError` becomes `PluginRevisionRejected`.

Log rejected user input in the service layer, and reject unknown Reader ids before anything is written. Also clean up the type-checker suppressions (spec D-13).

## Criteria covered
AC-15, AC-16, AC-17, AC-19

## Seams
- **Pure core:** `FieldError` and `ValidationRejected` in `service/validation.py`, including message building. Unit tests with no database.
- **Edge:** `require_reader` in `service/readers.py`; `create_plugin` and `create_channel` call it first. `_get_channel` logs `channel.not_found`. Tested on migrated SQLite with structlog's `capture_logs`.
- **CLI:** keeps its current per-exception handling here, with names updated. Ticket 02 consolidates it.

## Observability
- `info` `plugin_revision.rejected`: `reader_id`, `errors`.
- `info` `channel.not_found`: `reader_id`, `channel_id`.
- `info` `reader.not_found`: `reader_id`.

## Verification
- **AC-15:** an invalid Manifest raises `PluginRevisionRejected`, the plugin and plugin_revision row counts are unchanged, and the log event has its fields.
- **AC-16:** both an unknown Channel id and another Reader's Channel raise `ChannelNotFound` and log `channel.not_found`.
- **AC-17:** for an unknown Reader, `create_plugin` and `create_channel` raise `ReaderNotFound`, write no rows, and log `reader.not_found`. The CLI prints `no Reader <id>` and exits 1, with no traceback.
- **AC-19:** checks on the type hierarchy, `errors`, and message joining (including an empty `field` shown at the root). `ConfigError` and `ManifestError` no longer exist anywhere in `src/` or `tests/`.
- **D-13 (checked in review):**
  - the CLI's `_parse_config` uses `cast` after `isinstance`, with no `pyright: ignore`;
  - `binding_config.py` has one comment stating that jsonschema reports `required` and `additionalProperties` only on object instances.
- **Feeds deployment check:** "CLI, unknown Reader", together with ticket 02.

## Out of scope
- The `Logged to <path>.` pointer and the top-level handler (ticket 02).
- `plugin_id` on `plugin_revision.rejected` (plugin-drafts spec).
- Changing validation behavior or messages beyond the renames.
