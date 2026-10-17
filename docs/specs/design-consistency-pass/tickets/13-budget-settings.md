---
id: design-consistency-pass-13
title: Budget settings: defaults and changes without new Revisions
status: todo
blocked_by: [design-consistency-pass-12]
external: null
---

# Budget settings: defaults and changes without new Revisions

## Goal
Store the Channel budget on the Channel identity and the Reader and Provider caps as settings, with defaults and CLI commands to change them, effective on the next call.

## Criteria covered
AC-28, AC-29

## Seams
- Pure core: settings defaults.
- Edges: repositories; CLI `budget set`.

## Observability
- None new.

## Verification
- AC-28: changing a Channel budget creates no Channel Revision and applies to the next call.
- AC-29: defaults 500,000 / 2,000,000 / Provider uncapped.

## Out of scope
- Web App settings screens.
