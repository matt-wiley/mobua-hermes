---
id: design-consistency-pass-15
title: "Ephemeral Draft Test Run with Channel context and tagged accounting"
status: todo
blocked_by: [design-consistency-pass-06, design-consistency-pass-11, design-consistency-pass-12, design-consistency-pass-14]
external: null
---

# Ephemeral Draft Test Run with Channel context and tagged accounting

## Goal
Expose foreground Draft testing through CLI and API using saved inputs, a selected Channel, temporary config, the real process runner, and real Gateway budgets/accounting. Results are previews and are thrown away after delivery.

## Criteria covered
AC-70, AC-71, AC-72, AC-73, AC-80

## Seams
- Pure core: pre-execution eligibility/config/pin checks, preview validation, normal-versus-test side-effect policy.
- Edges: saved Draft/Channel input capture, declared Secret injection, actual restricted runner, scoped Gateway access, CLI/API result delivery.
- Reuse runner errors/limits/capped stderr without normal Plugin Run ingestion/log/Health orchestration. Do not create a durable test row, snapshots, test attribution, output, or logs.
- Use real migrated persistence and a fake Provider transport; real uid/environment/timeout/limit tests run inside the container. No fake Gateway token/budget placeholders.

## Observability
- No test output/stderr/failure history and no regular plugin_run.failed or news_item.rejected events for tests.
- Real calls retain ordinary Gateway outcome/metadata records and metrics; actual Provider errors update Model Health, with no test-driven linked Channel Health.
- No new metric families or labels.

## Verification
- AC-70: invalid Manifest/pins/config or foreign/unknown Draft/Channel rejects before any subprocess/Provider call and leaves state untouched.
- AC-71: successful, invalid-item, nonzero, timeout, and limit-exceeded previews include status/errors/capped stderr; zero ingestion and no durable test artifacts.
- AC-72: no Binding needed; use selected Channel Models, shared budgets, and only declared same-Reader Secrets. No config/schedule/lease/Binding changes.
- AC-73: usage has protected test_run and Plugin/Draft ids; unknown Model/budget refusal has no Provider call or Channel Health. Provider failure updates Model Health and usage only.
- AC-80: test exceptions never enter normal Plugin failure/item rejection/Channel Health paths; existing Gateway counters change for actual calls.
- Normal completion always revokes access and cleans files; active cancellation/disconnect is delivered next in 16. This ticket alone is not the complete Test Run feature.

## Deployment verification
- Own successful/rejected/failed test preview deployment checks: verify no Feed/config/lease/Health changes, actual token budgets/tags, and no retained test artifacts.

## Out of scope
- Active cancellation/disconnect and Draft edits during a test (16). No background jobs, durable test history/snapshots, persisted test-pass promotion gate, frontend editor.
