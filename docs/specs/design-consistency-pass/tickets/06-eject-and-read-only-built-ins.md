---
id: design-consistency-pass-06
title: Eject a Built-in Plugin; Built-ins are read-only
status: todo
blocked_by: [design-consistency-pass-05]
external: null
---

# Eject a Built-in Plugin; Built-ins are read-only

## Goal
Reject edits to Built-in Plugins and let a Reader Eject one into a new Reader-owned Plugin with no link back, via the CLI.

## Criteria covered
AC-8, AC-9

## Seams
- Pure core: eject copy (Manifest + code, creator = Reader, no reference).
- Edges: repositories, CLI `plugin eject`.

## Observability
- None new.

## Verification
- AC-8: editing or adding a Revision to a built-in is rejected.
- AC-9: ejected Plugin is Reader-owned, single Revision identical in Manifest and code, no reference to the built-in; a later built-in Revision leaves it unchanged.

## Out of scope
- Moving existing Bindings from the built-in to the ejected copy (use ticket 07's upgrade flow manually if needed).
