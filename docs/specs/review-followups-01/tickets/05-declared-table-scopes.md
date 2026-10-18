---
id: review-followups-01-05
title: Declared table scopes and schema rules
status: done
blocked_by: [review-followups-01-04]
external: null
---

# Declared table scopes and schema rules

## Goal
Each model declares `Table.info["scope"]` as `app`, `reader` or `channel`. A rule function in `tests/schema_rules.py` reports scope violations. The migrated database is checked against it. `READER_SCOPE_EXEMPT_TABLES` is removed. Also add the Built-in-style creator round-trip.

## Criteria covered
AC-1, AC-2, AC-3, AC-21

## Seams
- **Pure (test support):** `tests/schema_rules.py` takes a list of table descriptions (name, columns, foreign-key target tables, declared scope) and returns violations. Unit-test it on synthetic descriptions.
- **Edge:** build descriptions from `inspect(engine)` on the migrated SQLite database, plus `Base.metadata` table info. `alembic_version` counts as `app`.

## Observability
- None.

## Verification
- **AC-1:** in the migrated database, every table except `alembic_version` has a declared scope. A synthetic undeclared table is reported.
- **AC-2:** one unit test per rule:
  - a `reader` table without `reader_id`;
  - `reader` passing on its own `id`;
  - a `channel` table without `channel_id`;
  - `channel` passing on its own `id`;
  - an undeclared table;
  - a foreign key to a `channel` table from a non-`channel` table;
  - a clean schema with no violations.
- **AC-3:** the migrated database has no violations, and `READER_SCOPE_EXEMPT_TABLES` is gone. Replace the old foreign-key-heuristic test.
- **AC-21:** save a Plugin and Plugin Revision with `reader_id=None` and `created_by=creator_of(None)`, using the existing `a_built_in_plugin_revision` test helper. Commit, expire and read back: `created_by == "system"` and `reader_id is None`.
- **Migration:** `Table.info` is ORM-only, with no DDL. Confirm `compare_metadata` still reports no differences.

## Out of scope
- Moving migrations (ticket 04).
- The Revision update guard (ticket 06).
- Seeding Built-in Plugins (design-consistency-pass-05).
