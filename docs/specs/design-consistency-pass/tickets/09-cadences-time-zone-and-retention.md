---
id: design-consistency-pass-09
title: "Cadences, Reader time zone, and Retention Window validation"
status: todo
blocked_by: [design-consistency-pass-01]
external: null
---

# Cadences, Reader time zone, and Retention Window validation

## Goal
Persist interval/cron Collection and Publishing cadences, Reader time zone, and Retention Window with CLI configuration and save-time validation; compute next instants in UTC.

## Criteria covered
AC-46, AC-47, AC-48

## Seams
- Pure core: interval/cron parsing, zoneinfo day boundaries and next instants, longest cron gap, Retention Window comparison; injected clock.
- Edges: new migrations/settings, Channel Revision save, CLI. This supplies Reader time zone for budgets without depending on scheduling.

## Observability
- Reuse channel_revision.rejected with cadence/Retention Window fields.

## Verification
- AC-46: accept every 2h and a valid cron; reject malformed input.
- AC-47: America/Chicago 07:00 remains local 07:00 across DST and persists correct UTC instants.
- AC-48: default 14 days; reject a Retention Window no longer than the Publishing interval or longest cron gap.

## Deployment verification
- No standalone checklist item. Supply tested cadence/time-zone prerequisites to the scheduler and budget deployment checks.

## Out of scope
- Scheduler loop/Run Lease (19), per-Channel time zones, changing Channel edit behavior to Drafts.
