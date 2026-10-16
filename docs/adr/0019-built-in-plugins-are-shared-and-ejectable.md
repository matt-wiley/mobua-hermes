# 0019. Built-in Plugins are shared, system-owned, and ejectable

Status: Accepted
Date: 2026-10-16
Amends: ADRs 0007, 0018

## Context

ADR 0007 scopes every record to a Reader, and ADR 0018 lets a Plugin Binding reference only Plugins owned by the Channel's Reader. Built-in Plugins (e.g. RSS, ADR 0016) ship with the app. Copying them per Reader would satisfy both rules, but each copy would carry its own unrelated Revision history, losing the connection to the built-in's real history.

## Decision

- A **Built-in Plugin** is a single system-owned Plugin with no Reader id, read-only to every Reader. Its source of truth is the app's code: on each release, seeding adds a new system-created Plugin Revision only when the shipped code changed.
- A Plugin Binding may reference Revisions of Plugins owned by the Channel's Reader, **or** Revisions of Built-in Plugins. This exception lives in one place in the service layer, not in individual queries.
- Pinning (ADR 0018) applies unchanged: Channels stay on the built-in Revision they're bound to until explicitly moved, so "update available" is a comparison against the built-in's current Revision.
- A Reader who wants different behavior **ejects**: the app copies the Built-in Plugin's current Revision into a new Plugin owned by that Reader, created by that Reader. The copy has no link back to the built-in and is maintained independently from then on.

The exception is safe because ADR 0007 protects Reader data, and built-in code is not Reader data. Reader data used with built-ins (config on Plugin Bindings, Secrets) stays in Reader-owned records.

## Alternatives rejected

- **Per-Reader copies seeded at Reader creation.** Keeps ADR 0007 exceptionless, but splits one history into unrelated per-Reader histories and makes "same built-in release" unanswerable.
- **Fork-on-edit with lineage.** Tracks where a Reader's version came from, but nothing needs that link (no merging back, no diffs), and it couples the built-in's evolution to Readers who chose to diverge.

## Consequences

- One history per built-in; every Channel on a given built-in Revision shares the same row.
- Built-ins can evolve without regard to ejected copies, which never receive updates.
- Scoped Plugin queries must include Built-in Plugins through the one service-layer rule.
- Amends ADR 0007 (one exception: Built-in Plugins) and ADR 0018 (Binding ownership rule).
