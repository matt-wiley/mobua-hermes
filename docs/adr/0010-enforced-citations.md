# 0010. Citations are enforced through the Plugin contract and validated after writing

Status: Accepted
Date: 2026-10-16

## Context

Articles are LLM-written, so provenance must be traceable: the Reader must be able to follow any Article back to original upstream reporting. News Items are internal and transient, and Plugins may be arbitrary custom scripts.

## Decision

1. Every News Item must carry at least one Source Reference (URL, title, publisher, retrieved-at), original reporting first. Channels reject items without one at ingest and record it in Channel Health.
2. At Publish, the Source References of the News Items used become the Article's Citations, copied into the Article so they outlive the News Items.
3. After writing, every Citation in the Article must match a Source Reference from its Topic's News Items. If any Citation is unmatched, the Channel regenerates the Article, telling the writing Channel Model which Citations failed, up to a retry limit set on the Channel Revision (default 2). If it still fails, no Article is published, the failure and its unmatched Citations go to Channel Health, and the Topic's News Items stay unused for a later Publish until the Retention Window drops them.

## Alternatives rejected

- **Cite internal News Items.** Breaks once items expire and doesn't point at real reporting.
- **Optional or best-effort citations.** Custom scripts would silently drop provenance, and LLM-invented URLs would go unnoticed.

## Consequences

- Plugins that lose track of origins fail loudly.
- Validation adds a step to every Publish and may cost regenerations.
