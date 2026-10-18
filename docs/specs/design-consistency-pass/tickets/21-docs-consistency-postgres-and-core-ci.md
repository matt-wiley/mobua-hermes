---
id: design-consistency-pass-21
title: "ADR consistency, Postgres repository checks, and core CI"
status: done
blocked_by: [design-consistency-pass-04]
external: null
---

# ADR consistency, Postgres repository checks, and core CI

## Goal
Make architecture documentation consistency and SQLite/Postgres portability executable checks, then run them with the core gates in pull-request/main CI.

## Criteria covered
AC-55, AC-56, AC-58, AC-59

## Seams
- Pure core: ADR/index parsing and comparison of titles/status/reciprocal amendments; synthetic malformed inputs pin failure behavior.
- Edges: local check script and filesystem reads; migrated database fixtures selected by NEWS_TEST_DATABASE_URL; CI YAML with exact pinned Postgres image and full-SHA Actions.
- Default repository tests to SQLite; Postgres tests use psycopg 3. CI independently runs typecheck, lint/format/import boundaries, full SQLite suite, Postgres repositories/schema, and docs consistency.
- This ticket can run early after 04 and does not depend on scheduler 19; its number is the recommended final integration gate, not an artificial dependency.

## Observability
- No new app events or metrics. A failing local check prints a precise file/field discrepancy and exits nonzero; CI check names identify the gate.

## Verification
- AC-55/56: missing Status/Date, one-way amendments, duplicate/missing index rows, and mismatched title/status/amendments fail; current ADRs 0024/0025 pass.
- AC-58: real migrated repository/schema tests pass on Postgres and SQLite; a deliberately incompatible scratch construct proves the Postgres run uses Postgres.
- AC-59: actionlint validates YAML; PR and main triggers run every core gate, Postgres job, and local docs checker. A deliberately broken index fails CI.
- Maintain implementation-plan coverage/dependency links as documentation changes; preserve completed evidence and use the numbering map for historical references.
- Carried from ticket 04: on Postgres, an overlapping sibling promotion must wait on the Plugin-row claim, then get 409 `stale_current_selection` (no deadlock, no 503). Decide whether to pin READ COMMITTED in `create_engine_for` or rely on the documented default (README "Deferred decisions").

## Deployment verification
- Own docs-check and PR CI checklist items, plus actual Postgres portability evidence. A workflow file alone does not prove hosted CI ran; record deployment/hosted checks under Not verified until observed.

## Out of scope
- Web CI, container integration execution in hosted CI, branch-protection changes, publishing images, tracker writes.
