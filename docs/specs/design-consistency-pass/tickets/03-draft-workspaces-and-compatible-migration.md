---
id: design-consistency-pass-03
title: "Reader Plugin starter, Draft workspaces, and compatible migration"
status: todo
blocked_by: [design-consistency-pass-01]
external: null
---

# Reader Plugin starter, Draft workspaces, and compatible migration

## Goal
Create a Reader-owned Plugin with its valid starter and support multiple saved Drafts through shared services, CLI, and API. A Reader can export a Draft, edit files, explicitly save unfinished work with version checks, and discard it. Preserve existing databases.

## Criteria covered
AC-60, AC-61, AC-62, AC-63, AC-64

## Seams
- Pure core: same-Reader/same-Plugin parent eligibility, expected-version comparisons, workspace file selection.
- Edges: a new portable Alembic migration, starter assets, service-owned flushes with surface-owned commits, Typer commands, typed FastAPI routes, workspace export/import.
- Attach tests to real migrated databases and CLI/API transactions. Preserve completed migrations and existing Revision ids/contents/numbers/current pointers/Bindings; do not invent legacy ancestry.
- Store enough immutable Revision ancestry for later promotion; multiple Drafts share a parent. Export includes an expected-version marker outside Plugin implementation files. Save replaces the saved file set, so removed local code files are removed from the Draft.
- Draft/version metadata is excluded from exported runnable code; filenames remain within the workspace and run directory. A file-read/export failure reports an actionable error rather than silently saving partial contents.

## Observability
- info plugin_draft.deleted for explicit discard, with Reader/Plugin/Draft ids.
- info plugin_draft.conflict on stale saves, with operation and expected/actual version; never include source/config/credentials.
- Preserve configured CLI file logging, API stdout logging, safe unknown/foreign-resource rejection, and commit-before-success ordering. AC-81 integration ownership is ticket 04.

## Verification
- AC-60: fresh starter contains valid runnable no-op code; migration round-trip preserves preexisting records and introduces no fake root/parent relationships.
- AC-61: same-parent experiments coexist; reject foreign Reader, wrong Plugin parent, unknown target, and a system-owned fixture without inserting rows.
- AC-62: invalid TOML, unfinished code, and unpinned metadata save exactly as supplied, with no new Revision/current/Binding change.
- AC-63: CLI export/edit/save round-trip and API read agree, file removals are saved, stale versions fail with committed state unchanged, and local unsaved edits do not change the database.
- AC-64: delete only the requesting Reader own Draft; leave exported files, Revisions, and Bindings untouched.
- Test ownership and version rejection before any rollback and committed state through a separate session. Starter real restricted execution is verified by ticket 05.

## Deployment verification
- Own spec checklist: pre-Draft data migration and workspace create/export/save/discard portions of the lifecycle/conflict checks.

## Out of scope
- Promotion, dependency validation, Revision selection and immutable-delete enforcement (04).
- Subprocess Test Run endpoint/command (15-16); no inert endpoint pretending to execute tests.
- Built-in initial installation or Eject (07-08), frontend screens, external tracker writes.
