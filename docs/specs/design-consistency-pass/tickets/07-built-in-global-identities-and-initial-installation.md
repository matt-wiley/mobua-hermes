---
id: design-consistency-pass-07
title: "Globally identified Built-ins, shared scope, and initial RSS installation"
status: todo
blocked_by: [design-consistency-pass-04, design-consistency-pass-06]
external: null
---

# Globally identified Built-ins, shared scope, and initial RSS installation

## Goal
Ship a minimal RSS Built-in and install its supplied global Plugin/Revision UUIDs and development lineage on a fresh deployment. Expose the single shared ownership rule for listing and Binding eligibility.

## Criteria covered
AC-4, AC-7, AC-10, AC-54

## Seams
- Pure core: owner-or-Built-in access, bundled identity/content comparison for idempotent initial installation, local-only history presentation.
- Edges: bundled records/assets, initial installation path, repositories, RSS subprocess against a local fixture feed.
- Preserve supplied UUIDs, system provenance, and any supplied ancestry reference without requiring absent ancestor rows. Storage may differ from Reader Revision parent constraints.
- Do not create a local starter, temporary Draft, metadata-only history catalog, or locally generated Built-in ancestry.

## Observability
- info builtin_plugin.seeded with globally supplied Plugin/Revision UUIDs and content hash, once per initial record import. No repeated-startup duplicate event/record.

## Verification
- AC-7: two fresh databases get identical supplied UUIDs; repeat the same bundle without adding Revisions. Missing ancestor implementations do not cause placeholder records or appear in history.
- AC-4/10/54: two Readers list/bind shared Built-ins and their own Plugins; foreign Reader Plugins remain inaccessible.
- RSS fixture produces valid News Items and Source References with the real uv runtime.
- Existing local Revisions remain intact; no later-release update/rollback behavior is introduced.

## Deployment verification
- Own initial Built-in identity/local-history checks and RSS normal Collection demonstration: inspect News Items, Plugin OS user, and uv invocation. Read-only/Eject assertions are completed by 08.

## Out of scope
- Patch/release update delivery, application, rollback, and remote/full history are deferred.
- Eject/read-only mutation endpoints (08), full RSS feature set, update-available UI.
