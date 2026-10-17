---
id: design-consistency-pass-14
title: Publish tracer: grouping, per-step Models, writing, Model Attribution
status: todo
blocked_by: [design-consistency-pass-09, design-consistency-pass-11]
external: null
---

# Publish tracer: grouping, per-step Models, writing, Model Attribution

## Goal
Run a minimal Publish from the CLI: group unused News Items into Topics with schema-validated JSON, check past Articles, write one Article per Topic, each step using its resolved Channel Model, with retrieved content in delimited prompt blocks and Model Attribution on the Article.

## Criteria covered
AC-18, AC-38, AC-42, AC-51

## Seams
- Pure core: grouping-output validator; prompt builder with delimited, escaped data blocks; attribution builder.
- Edges: Gateway (fake adapter in tests); Article and Feed repositories; CLI `publish`.

## Observability
- None new beyond Gateway events.

## Verification
- AC-18: only writing set → all three steps use it; grouping set → grouping uses its Model.
- AC-38: attribution lists each step; survives purge of call records.
- AC-42: unknown and used ids discarded, empty Topic dropped, ungrouped items stay unused.
- AC-51: delimiter inside News Item text is escaped.
- Deployment checklist: "Publish an Article and inspect it via the CLI. Its Model Attribution lists each LLM step with Provider and Model id."

## Out of scope
- Citation retries (ticket 15).
- Writing-quality prompt work beyond producing a valid Article.
- Vetting (Channel contracts grill).
- Inbox/Aggregation semantics (Channel contracts grill).
