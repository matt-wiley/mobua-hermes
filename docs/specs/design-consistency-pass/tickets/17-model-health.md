---
id: design-consistency-pass-17
title: Model Health: call failures, hourly listing check, Provider tests
status: todo
blocked_by: [design-consistency-pass-11, design-consistency-pass-16]
external: null
---

# Model Health: call failures, hourly listing check, Provider tests

## Goal
Track Model Health per LLM Provider and Model from Gateway failures, an hourly model-listing check, and a 1-token test call on Provider save or test, and link affected Channels' Health to it.

## Criteria covered
AC-34, AC-35, AC-36, AC-37

## Seams
- Pure core: health state transitions from observations.
- Edges: Provider Adapter listing endpoint (contract test per adapter); scheduler job; CLI `provider test`.

## Observability
- `warning` `model_health.degraded` (Provider, Model, check type, failure kind).

## Verification
- AC-34: auth/not-found/rate-limit/timeout failures recorded.
- AC-35: hourly check spends 0 tokens; missing Model marked unhealthy.
- AC-36: save/test makes one 1-token call per enabled Model and records it.
- AC-37: Channel using an unhealthy Model gets a linked Health entry.
- Deployment checklist: "CLI: run the Provider test action. Model Health shows each enabled Model as healthy. Break the key and re-test: Model Health shows an auth failure, and Channels using that Provider show a linked Channel Health entry."

## Out of scope
- Periodic real-call checks (rejected alternative).
- Web App Model Health screen.
