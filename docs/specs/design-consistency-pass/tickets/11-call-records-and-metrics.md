---
id: design-consistency-pass-11
title: Gateway call records and Prometheus metrics
status: todo
blocked_by: [design-consistency-pass-09]
external: null
---

# Gateway call records and Prometheus metrics

## Goal
Write one durable call record per Gateway call and expose the four `gateway_*` Prometheus metrics at `/metrics`.

## Criteria covered
AC-31, AC-33

## Seams
- Pure core: call-record builder from a call outcome.
- Edges: repository; prometheus-client registry; FastAPI `/metrics` route.

## Observability
- Metrics: `gateway_calls_total{provider,model,outcome}`, `gateway_tokens_total{provider,model,direction}`, `gateway_call_duration_seconds{provider,model}`, `gateway_budget_refusals_total{budget,provider}` (the last is registered here and incremented by ticket 12).

## Verification
- AC-31: succeeded, failed, and refused calls each produce exactly one record with all fields.
- AC-33: `/metrics` exposes the four families; no `reader` or `channel` label.
- Deployment checklist: "`docker run` with a Master Key, then `GET /metrics`: all four `gateway_*` metric families are present, with no `reader` or `channel` labels."

## Out of scope
- Purging old records (ticket 16).
- Model-comparison UI (roadmap grill).
