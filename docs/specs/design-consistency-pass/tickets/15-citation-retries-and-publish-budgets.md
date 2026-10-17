---
id: design-consistency-pass-15
title: Citation retries, rejection, and budget exhaustion during Publish
status: todo
blocked_by: [design-consistency-pass-12, design-consistency-pass-14]
external: null
---

# Citation retries, rejection, and budget exhaustion during Publish

## Goal
Regenerate Articles with unmatched Citations up to the Channel Revision's retry limit, then reject them leaving the Topic's items unused, and stop a Publish cleanly when a budget runs out.

## Criteria covered
AC-30, AC-40, AC-41

## Seams
- Pure core: Citation matcher and retry-feedback builder; retry loop decision.
- Edges: Gateway (fake adapter scripted per attempt); Channel Health writer.

## Observability
- `warning` `article.citations_unmatched` (Channel id, Topic id, attempt, unmatched count).
- `error` `article.rejected` (Channel id, Topic id, attempts, unmatched Citations).

## Verification
- AC-40: two failures then success → published; retry prompts include the unmatched Citations.
- AC-41: limit 2 → 3 attempts, no Article, Health lists unmatched, items unused.
- AC-30: budget exhausted after first Article → 1 published, other Topics' items unused.
- Deployment checklist: "CLI: set a Channel budget to 1 token and trigger a Publish. Channel Health names the Channel budget, the Provider, and the Model; `gateway_budget_refusals_total{budget="channel"}` incremented; no new Channel Revision was created by the budget change."

## Out of scope
- Stripping unmatched Citations (rejected alternative).
