---
id: design-consistency-pass-10
title: "Gateway core, Channel Models, and call-driven Model Health"
status: todo
blocked_by: [design-consistency-pass-02, design-consistency-pass-05]
external: null
---

# Gateway core, Channel Models, and call-driven Model Health

## Goal
Build Provider Adapters and Channel Model resolution, with actual call-driven Model Health and Provider save/test actions now. Keep periodic listing checks with the later scheduler so Draft Test Runs need not wait for Publish/scheduling.

## Criteria covered
AC-17, AC-19, AC-34, AC-36, AC-37

## Seams
- Pure core: Channel Model validation/step inheritance, health transitions, normal-versus-test Channel Health effects.
- Edges: encrypted credential reads, OpenAI-compatible and Anthropic Adapter interfaces, typed Gateway service, Model Health persistence, CLI Provider test.
- Provider boundary fakes for domain tests and recorded/mocked HTTP contract tests for the actual adapters.
- Test-origin actual Provider errors update Model Health without creating a linked test-driven Channel Health entry; normal operation can surface the genuine Model Health issue.

## Observability
- warning gateway.call_failed and model_health.degraded with Provider/Model, safe error/check kind, latency, and trusted test origin when applicable; never credentials/prompt payloads.

## Verification
- AC-17/19: writing Model required; reject Models not enabled by the Reader. Test step inheritance, with full Publish use in 17.
- AC-34: actual auth/not-found/rate-limit/timeout failures update Model Health, including test-origin calls.
- AC-36: Provider save/test makes one real call per enabled Model with output limit 1 and records health. Use a fake Provider boundary, not mocked internal services.
- AC-37: normal Channel health links unhealthy configured Models; explicit test observation does not itself write linked Channel Health.
- Validate credential isolation and safe errors against sentinel keys. This ticket does not require scheduler 19.

## Deployment verification
- Own Provider test/Model Health checklist: healthy calls and broken-key observations, normal Channel links, and suppressed test-driven links.

## Out of scope
- Hourly model listing (19), Gateway token endpoint/helper and metadata forwarding (11), records/metrics (12), budgets (13-14), streaming/tool use/embeddings.
