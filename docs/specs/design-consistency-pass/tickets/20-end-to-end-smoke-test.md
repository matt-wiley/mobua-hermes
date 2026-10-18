---
id: design-consistency-pass-20
title: "Container smoke tests for scheduled publishing and Draft-to-Collection flow"
status: todo
blocked_by: [design-consistency-pass-07, design-consistency-pass-08, design-consistency-pass-16, design-consistency-pass-18, design-consistency-pass-19]
external: null
---

# Container smoke tests for scheduled publishing and Draft-to-Collection flow

## Goal
Prove the revised pieces compose in the container: scheduled RSS Collection/Publish and a saved Draft Test Run followed by promotion, explicit Binding, and normal Collection.

## Criteria covered
AC-57, AC-82

## Seams
- Real edges: restricted process runner/limits/uv, temporary cleanup, SQLite migrations/persistence, Gateway tokens/budgets/accounting, scheduler and Collection/Publish.
- Only fake boundaries are Provider transport and injected clock. Use local fixture feeds and pinned preseeded/local package sources; no actual remote Provider is required.
- Separate normal scheduled smoke and Draft-to-Collection smoke scenarios so failures identify the flow.

## Observability
- No new event families. Assert expected safe Draft events, tagged usage, normal run attribution, and absence of credential leaks or test failure/Health artifacts.

## Verification
- AC-57: one scheduler tick produces fixture News Items then a cited/attributed Article with call records; a second tick without new input produces no duplicate Article.
- AC-82: create/save/test with real runner, confirm ephemeral preview and usage tags with zero ingestion/Health/history, then promote/delete Draft, bind the new Revision explicitly, and collect its actual code.
- Verify permanent ancestry and stable normal Plugin Run attribution survive Draft removal. Check no sentinel key appears in env beyond the one declared Secret, logs, usage metadata, or output artifacts.

## Deployment verification
- Own final container integration of all Draft, normal Collection, Gateway usage, and scheduled Article checks. Document Not verified separately for actual deployment.

## Out of scope
- Real remote LLMs, external feeds, update delivery, Postgres/CI (21), Web App. Defects belong to the relevant owner ticket; this ticket adds integration evidence, not new product scope.
