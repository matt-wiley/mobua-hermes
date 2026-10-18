---
id: design-consistency-pass-19
title: "Scheduler, leases, Catch-up, retention purge, and periodic Model Health"
status: todo
blocked_by: [design-consistency-pass-05, design-consistency-pass-09, design-consistency-pass-10, design-consistency-pass-12, design-consistency-pass-18]
external: null
---

# Scheduler, leases, Catch-up, retention purge, and periodic Model Health

## Goal
Run the server scheduler for due Collections/Publishes, lease ordering/Catch-up, call-record purge, and hourly zero-token Model listing checks using the Model Health behavior already delivered in 10.

## Criteria covered
AC-6, AC-32, AC-35, AC-43, AC-44, AC-45

## Seams
- Pure core: due-run ordering, lease/defer and Catch-up decisions, retention cutoff, periodic listing observations; injected clock.
- Edges: server async poll loop, Run Lease persistence, Collection/Publish entry points, scheduled usage purge, Adapter model-listing calls.
- Add one listing contract test per Adapter. Keep call-driven and on-demand Model Health in 10; no reverse dependency from Test Runs to this scheduler.

## Observability
- info collection.skipped_no_bindings and scheduler.run_deferred_by_lease.
- warning run_lease.expired and model_health.degraded for periodic observations.
- Retain safe ids/check kinds without credentials or content.

## Verification
- AC-6: no Bindings skips Collection and flags Health; Publish still runs.
- AC-43/44: simultaneous overdue cadences collect before publishing; lease-blocked due times remain due and start after release.
- AC-45: five missed cadence slots coalesce to one run.
- AC-32: purge only usage records older than Reader retention; preserve newer records, metadata, and copied output attribution.
- AC-35: listing checks occur hourly, spend zero tokens, and mark missing Models unhealthy with normal links.
- Real selected-Channel tests do not acquire the lease or advance due times; combine with test executor through service boundaries where useful.

## Deployment verification
- Own no-Plugin skipped Collection/scheduler log deployment check and periodic Model Health/retention observations.

## Out of scope
- Multi-worker Postgres row-lock orchestration, Core agent cadence/Style workflow, periodic token-spending health calls, changing Test Runs into scheduled jobs.
