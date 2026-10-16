# 0003. Channels own their own history

Status: Accepted
Date: 2026-10-16

## Context

Channels write with awareness of what they've seen and reported. That history could live in the Core or inside each Channel.

## Decision

Each Channel owns its history: its Feed of News Items within the Retention Window, and its past Articles beyond it. The Core aggregates and presents; it does not supply Channels with context.

## Alternatives rejected

- **Core bundles recent Articles into requests.** Makes the Core responsible for each Channel's memory.
- **Core exposes a history query API.** Couples every Channel to a Core API for its own memory.

## Consequences

- Every Channel owns its data logically; see ADR 0013 for physical storage.
- Published Articles exist in two places: the Channel's history and the Core's aggregated view.
