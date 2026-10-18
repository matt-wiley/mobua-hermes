---
id: design-consistency-pass-17
title: "Publish tracer with Model Attribution and safe Article rendering"
status: todo
blocked_by: [design-consistency-pass-05, design-consistency-pass-10, design-consistency-pass-12]
external: null
---

# Publish tracer with Model Attribution and safe Article rendering

## Goal
Run a minimal CLI Publish from unused News Items through grouping, past-history check, writing, and safe rendered Article output, with per-step Channel Models and copied Model Attribution.

## Criteria covered
AC-18, AC-38, AC-42, AC-51, AC-52

## Seams
- Pure core: grouping validation, escaped/delimited prompt blocks, step resolution, attribution, and allowlist sanitization.
- Edges: Gateway with fake Provider boundary, Article/Feed repositories, CLI publish and Article inspection/rendering.
- Sanitization belongs at the Article display boundary from its first tracer; later Web App and feed surfaces reuse it.

## Observability
- No new events beyond existing Gateway observability. Keep retrieved data/prompt payloads out of operational logs.

## Verification
- AC-18: one writing Model supplies defaults; explicit grouping Model overrides only that step.
- AC-38: copied attribution covers every step and survives usage record purge.
- AC-42: discard unknown/used item ids and empty Topics; ungrouped items remain unused.
- AC-51: escaped delimiters prevent retrieved content from closing its data block.
- AC-52: displayed Article removes script/event handlers/javascript URLs and retains allowlisted formatting; exercise representative XSS payloads through the actual rendering function.

## Deployment verification
- Own Article inspection deployment check: safe formatting plus per-step Provider/Model attribution.

## Out of scope
- Citation retries/budget-exhaustion orchestration (18), prompt-quality work, vetting, Inbox/Aggregation contracts, Web App/feed UI.
