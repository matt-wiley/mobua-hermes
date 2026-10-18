# 0016. Channels and Plugins are database records with immutable revisions; Plugin code is data

Status: Accepted
Date: 2026-10-16
Amends: ADR 0015
Amended by: ADRs 0018, 0024

## Context

Channel and Plugin configuration could live in TOML files (versioned with git) or in the database. Files fragment data across two stores, and git becomes a second, replay-based database. Provenance (ADR 0010) makes it valuable to know which configuration produced an Article.

## Decision

Channels and Plugins live in the database. Each has an identity row plus immutable revision rows (`channel_revision`, `plugin_revision`): full config, revision number, timestamp, optional note. The identity row points at its current revision; rollback repoints to an older one. Collections, Publishes, and Articles record the revisions that produced them.

A Plugin Revision stores its Plugin Manifest and its code files as text. At run time the Channel writes them to a temporary directory and runs them there; the stdin/stdout contract from ADR 0015 is unchanged.

Plugin config: amended by ADR 0018. A Plugin Revision holds the Manifest and code only; per-Channel config lives on Plugin Bindings in the Channel Revision, each pinned to one Plugin Revision.

Plugin editing and history: amended by ADR 0024. Plugins have multiple disposable mutable
Drafts based on immutable Revisions. Promotion creates a permanent Revision and deletes the
Draft; every Plugin starts with a valid starter root Revision. Channel editing is unchanged.

## Alternatives rejected

- **TOML files plus git.** Versionable and hand-editable, but splits data across two stores and relationships can't be enforced.
- **Temporal rows (valid-from/valid-to).** Fewer tables, but every query needs current-version filtering and pinning foreign keys to a version is awkward.
- **Event sourcing / audit log.** Powerful, but it's a replay database by another name.
- **SQLAlchemy-Continuum or similar.** Less code, but hidden machinery to maintain.

## Consequences

- Storing code as data is a known smell, accepted deliberately to keep all entities and relationships in one place.
- Configuration lineage: any Article traces back to the exact Channel and Plugin Revisions that produced it.
- Built-in Plugins (e.g. RSS) are seeded as records.
- Running a Plugin requires materializing its files first.
- TOML remains the manifest format; the Web App's TOML editor edits records, not files.
