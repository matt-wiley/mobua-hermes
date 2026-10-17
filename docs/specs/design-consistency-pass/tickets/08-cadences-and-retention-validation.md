---
id: design-consistency-pass-08
title: Interval and cron cadences, Reader time zone, Retention Window validation
status: todo
blocked_by: [design-consistency-pass-01]
external: null
---

# Interval and cron cadences, Reader time zone, Retention Window validation

## Goal
Add Collection and Publishing cadences (interval or cron) and the Retention Window to Channel Revisions, the Reader time zone setting, next-run computation in UTC, and save-time validation.

## Criteria covered
AC-46, AC-47, AC-48

## Seams
- Pure core: cadence parser; next-run calculator with `zoneinfo`; longest-gap computation for cron; Retention Window check. All pure, clock injected.
- Edges: Channel Revision save path; CLI flags.

## Observability
- Adds cadence and Retention Window reasons to `channel_revision.rejected`.

## Verification
- AC-46: `every 2h` and `0 7 * * *` accepted; malformed rejected.
- AC-47: 07:00 America/Chicago on both sides of a DST change, stored as correct UTC instants.
- AC-48: default 14 days; window ≤ Publishing interval rejected; cron uses the longest gap.

## Out of scope
- The scheduler loop and leases (ticket 16).
- Per-Channel time zones.
