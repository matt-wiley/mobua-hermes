---
id: design-consistency-pass-07
title: Pinned Bindings and explicit multi-Channel upgrades
status: todo
blocked_by: [design-consistency-pass-03]
external: null
---

# Pinned Bindings and explicit multi-Channel upgrades

## Goal
Prove that Bindings run their pinned Plugin Revision, and add the CLI operation that moves selected Channels to a new Plugin Revision, creating new Channel Revisions and re-validating config, reporting Channels that fail.

## Criteria covered
AC-2, AC-3

## Seams
- Pure core: upgrade planner (per Channel: validate config against target schema → move or report).
- Edges: repositories (transaction per Channel), CLI `binding upgrade`.

## Observability
- Reuses `channel_revision.rejected` for Channels that fail re-validation.

## Verification
- AC-2: after editing the Plugin, a Collection still runs Revision 1's code.
- AC-3: of three Channels, two move and get new Channel Revisions; the third is reported with its validation error and unchanged.

## Out of scope
- "Update available" detection and UI.
- Web App batch action.
