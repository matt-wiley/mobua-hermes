---
id: design-consistency-pass-16
title: Scheduler loop: due runs, ordering, Run Lease, Catch-up, purge
status: todo
blocked_by: [design-consistency-pass-03, design-consistency-pass-08, design-consistency-pass-14]
external: null
---

# Scheduler loop: due runs, ordering, Run Lease, Catch-up, purge

## Goal
Run the service-layer scheduler in the server process: start due Collections and Publishes, Collection before Publish, keep lease-blocked runs due, coalesce missed slots, skip Collections with no Bindings, and run the scheduled call-record purge.

## Criteria covered
AC-6, AC-32, AC-43, AC-44, AC-45

## Seams
- Pure core: due-run selection and ordering; Catch-up coalescing. Clock injected.
- Edges: async poll loop; Run Lease rows; Collection/Publish entry points.

## Observability
- `info` `collection.skipped_no_bindings` (Channel id).
- `info` `scheduler.run_deferred_by_lease` (Channel id, cadence, lease holder run id).
- `warning` `run_lease.expired` (Channel id, run id, held duration).

## Verification
- AC-6: zero Bindings → no Collection, Health "no Plugins attached", Publish still runs.
- AC-43: both overdue → Publish starts after Collection completes.
- AC-44: next-run-at not advanced while blocked; starts on first poll after release.
- AC-45: 5 missed slots → 1 Collection.
- AC-32: records older than retention (default 90 days) removed; newer kept.
- Deployment checklist: "CLI: create a Channel with no Plugin Bindings and wait one Collection interval. Channel Health shows "no Plugins attached", and `docker logs` shows `collection.skipped_no_bindings`."

## Out of scope
- Multi-worker scheduling with Postgres row locks.
- Core agent cadence (Style grill).
