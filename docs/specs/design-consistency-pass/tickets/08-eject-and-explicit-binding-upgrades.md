---
id: design-consistency-pass-08
title: "Eject Built-ins and explicitly upgrade pinned Bindings"
status: todo
blocked_by: [design-consistency-pass-04, design-consistency-pass-05, design-consistency-pass-07]
external: null
---

# Eject Built-ins and explicitly upgrade pinned Bindings

## Goal
Provide a usable independent Eject copy and explicit selected-Channel Binding upgrades. Prove current-pointer selection and Draft/promotion changes never silently change pinned execution.

## Criteria covered
AC-2, AC-3, AC-8, AC-9

## Seams
- Pure core: Eject initialization and per-Channel target-schema validation/upgrade planning.
- Edges: Reader-owned starter plus copied Revision 2 in one transaction, read-only Built-in service checks, CLI Eject/Binding commands, real runner for pinned execution.
- Expose Reader Draft/history APIs from 03/04 with the same Built-in restrictions; moving Bindings still creates Channel Revisions.

## Observability
- Reuse channel_revision.rejected for failed upgrade validations. No new event family for Eject.

## Verification
- AC-8: Reader edit/Draft/add-Revision/current-pointer mutations on Built-ins fail without changes; listing and Binding remain available.
- AC-9: Eject creates starter 1 and copied current 2 with parent 1 and Reader creator, no Built-in lineage/reference, and no automatic Binding move.
- AC-2: edit/save/promote a Draft and change Plugin current selection; a real Collection still executes the pinned original code.
- AC-3: two valid Channels move to validated new Channel Revisions; the invalid third reports fields and remains unchanged. Use per-Channel transactions.

## Deployment verification
- Own read-only/Eject portions of Built-in checklist and demonstrate selecting Plugin current does not move an existing Binding.

## Out of scope
- No Built-in merging/updates, automatic Bindings following current, batch Web App screens, or Revision deletion.
