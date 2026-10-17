---
id: design-consistency-pass-09
title: LLM Gateway core, Provider Adapters, and Channel Models
status: todo
blocked_by: [design-consistency-pass-02]
external: null
---

# LLM Gateway core, Provider Adapters, and Channel Models

## Goal
Build the Gateway's single call (messages in, text or schema-validated JSON out, token usage) with OpenAI-compatible and Anthropic Provider Adapters, decrypting provider credentials only inside the Gateway, and add Channel Models with per-step mapping to Channel Revisions.

## Criteria covered
AC-17, AC-19

## Seams
- Pure core: Channel Model validation (writing step required, names map to enabled Models); step → Channel Model resolution with inheritance.
- Edges: Provider Adapter interface with a fake for tests; one contract test per real adapter (recorded/mocked HTTP).

## Observability
- `warning` `gateway.call_failed` (Provider, Model, error kind, latency).

## Verification
- AC-17: Channel Revision without a writing-step Channel Model rejected.
- AC-19: mapping to a Model the Reader hasn't enabled rejected.
- Unit-test step inheritance here; AC-18's end-to-end check is in ticket 14.

## Out of scope
- Gateway Tokens and Plugin calls (ticket 10).
- Budgets, call records, metrics (tickets 11–13).
- Streaming, tool use, embeddings.
