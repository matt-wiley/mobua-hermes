---
id: design-consistency-pass-12
title: Nested daily token budgets enforced in the Gateway
status: todo
blocked_by: [design-consistency-pass-11]
external: null
---

# Nested daily token budgets enforced in the Gateway

## Goal
Refuse Gateway calls when the Channel, Provider, or Reader daily budget is exhausted, resetting at midnight in the Reader's time zone, and record refusals in Channel Health naming the budget, Provider, and Model.

## Criteria covered
AC-24, AC-25, AC-26, AC-27

## Seams
- Pure core: budget decision (usage + limits → allow or refuse with budget named); day boundary in Reader time zone. Clock injected.
- Edges: usage totals from call records; Channel Health writer.

## Observability
- `warning` `gateway.budget_refused` (Reader id, Channel id, budget, Provider, Model, used, limit); increments `gateway_budget_refusals_total`.

## Verification
- AC-24: 990/1000 used → refused before provider call; Health names Channel budget, Provider, Model.
- AC-25: exhausted Provider cap refuses that Provider only.
- AC-26: refused until 00:00 America/Chicago, allowed after.
- AC-27: unlimited never refuses.

## Out of scope
- Budget settings CLI and defaults (ticket 13).
- Dollar budgets (non-goal).
