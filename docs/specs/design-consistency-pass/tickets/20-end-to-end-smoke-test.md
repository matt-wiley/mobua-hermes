---
id: design-consistency-pass-20
title: End-to-end smoke test: scheduler tick to attributed Article
status: todo
blocked_by: [design-consistency-pass-05, design-consistency-pass-15, design-consistency-pass-16, design-consistency-pass-17]
external: null
---

# End-to-end smoke test: scheduler tick to attributed Article

## Goal
Prove the pieces compose. One test drives a Channel from a scheduler tick through a real Plugin Run, Collection, the Gateway and Publish to an Article in the Inbox, with no fakes except the Provider Adapter and the clock.

## Criteria covered
AC-57

## Seams
- Edges, all real: the scheduler loop, the Plugin Run launcher (uid switch, clean env, rlimits, `uv run`), SQLite repositories, the LLM Gateway.
- Fakes: a fake Provider Adapter returning canned grouping and writing output whose Citations match the fixture feed; the injected clock.
- Fixture: a local RSS file (or a local HTTP server) the RSS Built-in Plugin reads, so no network is needed.
- Runs in the container image, alongside the launcher integration tests from tickets 03 and 04, behind the same pytest marker.

## Observability
- None new. The test asserts the absence of `plugin_run.failed`, `news_item.rejected` and `article.rejected` events, and one call record per LLM step.

## Verification
- AC-57: after one tick, the Feed holds the fixture's News Items and they are marked used. The Inbox holds at least one Article whose Citations all match fixture Source References and whose Model Attribution names the fake Model for each LLM step. Call records exist for every LLM step and nothing else.
- Also check that a second tick with no new feed items produces no new Article, so dedup holds across the whole flow.

## Out of scope
- New behavior. If the test exposes a defect, fix it only if it's a one-line wiring fix; otherwise report it against the owning ticket.
- Real LLM Providers, the network, Postgres (ticket 21), and the Web App.
