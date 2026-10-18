---
id: design-consistency-pass-18
title: "Citation retries, Article rejection, and Publish budget exhaustion"
status: todo
blocked_by: [design-consistency-pass-13, design-consistency-pass-14, design-consistency-pass-17]
external: null
---

# Citation retries, Article rejection, and Publish budget exhaustion

## Goal
Regenerate unmatched Citations within the configured retry limit, then reject without consuming News Items; stop a Publish cleanly when its shared budget is exhausted.

## Criteria covered
AC-30, AC-40, AC-41

## Seams
- Pure core: Source Reference/Citation matching, retry-feedback builder, retry/stop decisions.
- Edges: real Feed/Article/Health persistence, Gateway with scripted fake Provider boundary, actual budget settings CLI.

## Observability
- warning article.citations_unmatched with Channel/Topic/attempt/unmatched count.
- error article.rejected with Channel/Topic/attempts/unmatched Citations, without credentials.

## Verification
- AC-40: two unmatched attempts followed by success publish; retry prompts identify unmatched Citations.
- AC-41: retry limit 2 permits three attempts then no Article; Health records unmatched Citations and News Items stay unused.
- AC-30: after first Article consumes available budget, other Topics remain unused and their Articles are not published. All real calls/retries retain accounting and attribution.

## Deployment verification
- Own Publish budget deployment check: set budget to 1, inspect normal Channel Health naming budget/Provider/Model, metric increment, and unchanged Channel Revision count.

## Out of scope
- Removing unmatched Citations silently, per-test budget exceptions, prompt-quality work.
