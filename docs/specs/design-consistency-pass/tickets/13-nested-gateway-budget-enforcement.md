---
id: design-consistency-pass-13
title: "Nested daily token budget enforcement"
status: todo
blocked_by: [design-consistency-pass-09, design-consistency-pass-12]
external: null
---

# Nested daily token budget enforcement

## Goal
Enforce Channel, Provider, and Reader daily token budgets for normal and ephemeral test callers, with safe refusals and Reader-local midnight resets.

## Criteria covered
AC-24, AC-25, AC-26, AC-27

## Seams
- Pure core: usage/limits/time-zone decision, unlimited settings, daily window boundaries.
- Edges: real usage totals, atomic concurrent budget accounting/admission, normal Channel Health writer and trusted test exception.
- Tests and ordinary Channel calls consume the same relevant budgets, including when overlapping; do not rely on the GIL for reservation/accounting.

## Observability
- warning gateway.budget_refused with Reader/Channel, budget kind, Provider/Model, used/limit, and trusted test origin.
- Increment existing gateway_budget_refusals_total; normal refusals create Channel Health, test refusals do not.

## Verification
- AC-24: 990/1000 refuses before Provider invocation; normal Health names the exhausted budget. Trusted test refusal has equivalent record/metric but no Channel Health.
- AC-25: exhausted Provider cap affects that Provider only; Reader and Channel constraints also apply.
- AC-26: America/Chicago reset behavior across local midnight, including DST boundaries.
- AC-27: explicit unlimited never refuses for that budget.
- Verify actual overlapping normal/test admissions cannot bypass shared limits; use real persistence and controlled Provider boundary concurrency.

## Deployment verification
- Own refusal accounting/Health assertions used in Publish and Test Run checks. The settings CLI demonstration is completed by 14/18.

## Out of scope
- Settings surfaces/default wiring (14), dollar budgets, per-test exemption or separate budget pool.
