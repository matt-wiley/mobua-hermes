---
id: design-consistency-pass-10
title: Gateway Tokens and Plugin LLM turns by Channel Model name
status: todo
blocked_by: [design-consistency-pass-03, design-consistency-pass-09]
external: null
---

# Gateway Tokens and Plugin LLM turns by Channel Model name

## Goal
Issue short-lived Gateway Tokens per Plugin Run scoped to the Channel's Channel Models, give Plugins a `channel.model(name).send(...)` helper, refuse unknown names, and attach Model Attribution to Plugin Runs.

## Criteria covered
AC-20, AC-21, AC-22, AC-39

## Seams
- Pure core: token claims/expiry check; name resolution; Plugin Run attribution builder.
- Edges: Gateway HTTP endpoint; Python helper module shipped to Plugins; launcher passes URL + token.

## Observability
- `warning` `channel_model.unknown` (Channel id, Plugin Run id, requested name).

## Verification
- AC-20: any bound Plugin reaches the Model mapped to `vetter`.
- AC-21: unknown name → error naming it, no provider call, Channel Health entry.
- AC-22: Channel A's token refused for Channel B; expired token refused (lifetime = Manifest timeout + 60 s).
- AC-39: Plugin Run lists one attribution entry per turn.

## Out of scope
- Budgets (ticket 12).
- Per-Binding access control (non-goal).
