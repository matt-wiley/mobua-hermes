---
id: design-consistency-pass-04
title: "Promote Drafts and select permanent Revision history"
status: done
blocked_by: [design-consistency-pass-03]
external: null
---

# Promote Drafts and select permanent Revision history

## Goal
Finish the Draft lifecycle through CLI and API: validate and atomically promote a versioned Draft, retain a permanent branching Revision history, and select any existing current Revision without moving Bindings. Deliver exact-pin validation now so process execution can depend on it.

## Criteria covered
AC-49, AC-65, AC-66, AC-67, AC-68, AC-69, AC-81

## Seams
- Pure core: Manifest and PEP 723 exact-pin validation; promotion eligibility and expected-version/current-selection checks; permanent Revision rules.
- Edges: transactionally allocate Revision numbers from the complete history, insert child ancestry, change current pointer, and delete the promoted Draft; CLI/API responses follow commit.
- A promotion from a non-current parent explicitly confirms the expected current selection. Concurrent pointer changes require fresh confirmation; do not merge.
- Extend Plugin Revision immutability to deletion. Draft mutability/deletion and the new migration boundary are explicit exceptions; do not invent Channel or Binding deletion policy.
- Use real migrated SQLite transactions and schema rules; Postgres verification is owned by 21.

## Observability
- info plugin_draft.promoted with Reader/Plugin/Draft/parent/new Revision ids.
- info plugin_draft.rejected with safe reason/field codes for rejected promotion.
- info plugin_draft.conflict for stale promotion or current-selection confirmation.
- Own AC-81: exercise events from 03/04 using both actual CLI log files and API/server logging; exclude Manifest/code/config and sentinel credential material. No new metrics.

## Verification
- AC-49: reject unpinned Python dependencies, accept exact pins and no-dependency scripts; reuse the parser at test validation and runtime rather than defining it in 06.
- AC-65: successful promotion copies/deletes atomically; validation, stale versions, and actual transaction failure preserve Draft/current/count/Bindings before rollback and after failed commits.
- AC-66: promote sibling and older-parent Drafts; verify ancestry, untouched sibling Drafts, confirmation requirements, distinct numbers, and allocation after current-pointer rollback.
- AC-67/69: CLI/API history and current selection agree, reject wrong Plugin/Reader selections, and report success only after commit. No retained successful test is required.
- AC-68: loaded Revision changes/deletes fail; retained source/ancestry/metadata are unchanged; no archive/delete surface exists. Draft save/delete remains functional.
- AC-81: verify all assigned event levels and safe fields, including deletion/conflict events delivered in 03.

## Deployment verification
- Own spec lifecycle promotion/rejection/history selection checks and stale promotion/current-selection checks. Inspect both successful and rejected operation logs.

## Out of scope
- No process execution, test-result gate, automatic merging, Channel Drafts, Revision archival/deletion, or automatic Binding upgrades.
- Do not rewrite the completed 01/02 tickets or their evidence; this is additive behavior. No new migration is needed: ticket 03's schema plus the ORM guard (AC-68 "service/ORM") suffice.
