---
id: design-consistency-pass-21
title: "Postgres repository checks and core CI"
status: done
blocked_by: [design-consistency-pass-04]
external: null
---

# Postgres repository checks and core CI

## Goal
Make SQLite/Postgres portability executable checks and run them with the core gates in pull-request/main CI.

## Scope amendment (2026-10-18)
The user canceled all ADR-checking work because its fragility and maintenance cost outweigh its current value. Remove the checker, its tests, dependency declaration, CI job, and dedicated repair/review artifacts. AC-55 and AC-56 are withdrawn; ADRs and their index remain maintained by hand. The Postgres fixtures, READ COMMITTED pin, promotion-race coverage, and application CI gates remain in scope. Track this work locally; do not create GitHub issues.

## Criteria covered
AC-58, AC-59

## Seams
- Edges: migrated database fixtures selected by NEWS_TEST_DATABASE_URL; CI YAML with exact pinned Postgres image and full-SHA Actions.
- Default repository tests to SQLite; Postgres tests use psycopg 3. CI independently runs typecheck, lint/format/import boundaries, full SQLite suite, and Postgres repositories/schema.
- This ticket can run early after 04 and does not depend on scheduler 19; its number is the recommended final integration gate, not an artificial dependency.

## Observability
- No new app events or metrics. CI check names identify the gate and a failing step fails its job.

## Verification
- AC-58: real migrated repository/schema tests pass on Postgres and SQLite; a deliberately incompatible scratch construct proves the Postgres run uses Postgres.
- AC-59: actionlint validates YAML; PR and main triggers run the four application CI jobs. The workflow contract rejects additional jobs, including the canceled ADR check.
- Maintain implementation-plan coverage/dependency links as documentation changes; preserve completed evidence and use the numbering map for historical references.
- Carried from ticket 04: on Postgres, an overlapping sibling promotion must wait on the Plugin-row claim, then get 409 `stale_current_selection` (no deadlock, no 503). Decide whether to pin READ COMMITTED in `create_engine_for` or rely on the documented default (README "Deferred decisions").

## Deployment verification
- Own the PR/main CI checklist item and actual Postgres portability evidence. A workflow file alone does not prove hosted CI ran; record deployment/hosted checks under Not verified until observed.

## Out of scope
- Automated ADR checking, Web CI, container integration execution in hosted CI, branch-protection changes, publishing images, external tracker writes.
