---
id: design-consistency-pass-12
title: "Gateway call records, analysis tags, and Prometheus metrics"
status: todo
blocked_by: [design-consistency-pass-11]
external: null
---

# Gateway call records, analysis tags, and Prometheus metrics

## Goal
Persist exactly one record for each Gateway call outcome, including extensible protected metadata, and expose the existing four metric families without adding arbitrary tag labels.

## Criteria covered
AC-31, AC-33, AC-79

## Seams
- Pure core: call-record builder from success/error/refusal and trusted caller context.
- Edges: new portable usage schema, Reader-scoped usage access, prometheus-client registry and API metrics endpoint.
- Store historical test Plugin/Draft ids as retained values, not mandatory foreign keys to disposable Draft or nonexistent durable test-run records.
- Keep credential material out of metadata and logs; identity tags are supplied by trusted scope, not Plugin claims.

## Observability
- gateway_calls_total, gateway_tokens_total, gateway_call_duration_seconds, gateway_budget_refusals_total retain exactly the specified bounded labels.
- No extra application metrics. Preserve safe existing Gateway failure logging and test origin.

## Verification
- AC-31: exactly one record for success, Provider error, unknown Model, and refused authorization/budget outcomes as fields become available; no duplicate retry bookkeeping.
- AC-79: metadata persists with all outcomes after Draft deletion, with no snapshots or credential values. Query through Reader scope in tests; normal purge retention is 19.
- AC-33: four families present and no Reader, Channel, Draft, arbitrary tag-key, or arbitrary tag-value labels.
- Use real migrated usage persistence and an isolated Prometheus registry; Provider transport remains the fake boundary.

## Deployment verification
- Own metrics deployment check: GET /metrics shows all four families and correct bounded labels. Provide tagged-record inspection for later Test Run checks.

## Out of scope
- Budget decision/enforcement (13), purge scheduling (19), analysis UI or external telemetry integrations, storing prompts/responses/test output.
