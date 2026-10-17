---
id: design-consistency-pass-01
title: Scaffold the core module and the revisioned Channel/Plugin data model
status: todo
blocked_by: []
external: null
---

# Scaffold the core module and the revisioned Channel/Plugin data model

## Goal
Create the `src/news` package (service/api/cli layers, uv, ruff, pyright, pytest, import-linter), SQLAlchemy 2.1 + Alembic on SQLite (WAL), and the Reader, Channel + Channel Revision, Plugin + Plugin Revision, and Plugin Binding records, with a CLI to create a Plugin, a Channel, and a Binding whose config is validated against the Plugin Revision's schema.

## Criteria covered
AC-1, AC-5, AC-53

## Seams
- Pure core: JSON Schema validation of Binding config; Revision creation rules.
- Edges: SQLAlchemy repositories (tested on SQLite); Typer CLI commands.
- Schema test (AC-53) introspects the Alembic-migrated database.

## Observability
- `info` `channel_revision.rejected` (Channel id, validation errors). Later tickets add reasons to this event.

## Verification
- AC-1: happy path (valid config saves); failure (missing required field rejected, no Revision created); boundary (extra/unknown fields per schema `additionalProperties`).
- AC-5: Reader-created Revision records the Reader id; a Revision created through the seeding path records `system` (seeding itself is ticket 05; test the creator field directly).
- AC-53: every table has a Reader id column except declared app-wide tables; Channel-owned tables have a Channel id column.
- `uv run lint-imports` enforces api/cli → service only (ADR 0017).
- After this ticket, re-run `/mobua-swe:setup` so the core module's commands are run and `commands_verified` is set.

## Out of scope
- Built-in Plugins, seeding, Eject (tickets 05–06).
- Running Plugins or Collections (ticket 03).
- Channel Models, cadences, Retention Window fields beyond placeholders (tickets 08–09).
- The FastAPI app beyond an empty app object; the web module.
