# 0007. All data is scoped to a Reader; Channels have one owner

Status: Accepted
Date: 2026-10-16
Amended by: ADR 0019

## Context

v1 is single-user, but multiple users should be possible later without a rewrite. Articles are written using one Reader's Style.

## Decision

Every record carries a Reader id from day one, except Built-in Plugins and their Revisions (ADR 0019) and app-wide records that hold no Reader data (e.g. schema version). Records that belong to a Channel also carry its Channel id. Examples: Channels and their Revisions, Plugins, Plugin Runs, News Items, Articles, the Style, Feedback, Secrets, LLM Providers. Each Channel is owned by exactly one Reader.

Exception: amended by ADR 0019. Built-in Plugins are system-owned and carry no Reader id.

## Alternatives rejected

- **Single-user data model, add users later.** Simpler now, but retrofitting ownership across every table is painful.
- **Shared Channels across Readers.** Articles would either ignore each Reader's Style or be rewritten per Reader.

## Consequences

- Slight overhead in v1 for a single user.
- Sharing Channels or a public catalog later would share configuration, not Articles, and is out of scope for now.
