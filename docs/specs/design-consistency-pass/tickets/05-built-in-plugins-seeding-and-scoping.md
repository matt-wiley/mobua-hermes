---
id: design-consistency-pass-05
title: Built-in Plugins: seeding, shared scoping rule, and a minimal RSS built-in
status: todo
blocked_by: [design-consistency-pass-04]
external: null
---

# Built-in Plugins: seeding, shared scoping rule, and a minimal RSS built-in

## Goal
Seed system-owned Built-in Plugins from app code (new Revision only when the content hash changes), add the single service-layer rule that lets Bindings and queries include Built-in Plugins, and ship a minimal RSS Built-in Plugin that produces News Items.

## Criteria covered
AC-4, AC-7, AC-10, AC-54

## Seams
- Pure core: content-hash comparison; Binding eligibility rule (owner or built-in).
- Edges: seeding on startup; repositories.
- The RSS built-in is tested against a local fixture feed.

## Observability
- `info` `builtin_plugin.seeded` (Built-in Plugin, new Revision id, content hash).

## Verification
- AC-7: unchanged code adds no Revision; changed code adds exactly one.
- AC-4: binding to another Reader's Plugin rejected; to a built-in accepted.
- AC-10 / AC-54: built-in rows have no Reader id; Readers A and B both see built-ins and only their own Plugins.
- Deployment checklist: "CLI: bind the RSS Built-in Plugin and run a Collection. News Items appear in the Feed, and the Plugin Run's process runs as the Plugin OS user via `uv run`."

## Out of scope
- Eject and read-only enforcement (ticket 06).
- Full RSS feature set (enclosures, auth feeds, etc.) beyond producing valid News Items with Source References.
- "Update available" UI.
