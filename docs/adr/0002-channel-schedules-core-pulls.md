# 0002. Channels run Collection and Publishing schedules; the Core pulls

Status: Accepted
Date: 2026-10-16

## Context

Information must be gathered, written up, and shown to the reader. Scheduling could sit in the Core, in each Channel, or be split.

## Decision

Each Channel runs two independent schedules: a Collection cadence (run the Plugin, add News Items to its Feed) and a Publishing cadence (write Articles into its Inbox). The Core does not trigger writing; it only pulls Published Articles from Inboxes for Aggregation.

## Alternatives rejected

- **One Core scheduler that asks Channels to fetch and write synchronously.** Couples gathering to reading frequency and blocks the Core on slow fetches and LLM writes.
- **Core triggers writing on its schedule.** Makes the Core responsible for every Channel's rhythm.

## Consequences

- Channels are autonomous; the Core is a reader of their Inboxes.
- A shared scheduler in the service layer starts each Channel's runs when its own cadence says they are due (ADR 0014); it does not impose a rhythm.
- Article freshness depends on each Channel's Publishing cadence, not on when the Core pulls.
