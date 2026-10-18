# 0018. Channels use Plugins through Plugin Bindings pinned to a Plugin Revision

Status: Accepted
Date: 2026-10-16
Amends: ADR 0016
Amended by: ADRs 0019, 0024

## Context

ADR 0016 stores a Plugin's full config on its Plugin Revision. That works for a script used by one Channel, but not for a Plugin used by several: the built-in RSS Plugin is one seeded record that every RSS Channel needs with a different feed URL, and a Reader's own scraper can't be reused without copying it. Provenance (ADR 0010) also requires knowing exactly which code and config produced an Article.

## Decision

Split what a Plugin is from how a Channel uses it.

- A **Plugin** is a named identity owned by one Reader, pointing at its current Plugin Revision. A **Plugin Revision** is immutable and holds the Plugin Manifest (including the config schema) and code, and records who created it: a Reader, or the system for seeded Built-in Plugins.
- A **Channel** keeps its identity row and immutable **Channel Revisions** (unchanged from ADR 0016).
- A Channel Revision holds one **Plugin Binding** per Plugin it uses. A Binding references one exact Plugin Revision, never the Plugin identity, and carries that Channel's config for it, validated against that Revision's config schema.
- A Binding may only reference Revisions of Plugins owned by the Channel's Reader, or of Built-in Plugins (amended by ADR 0019).
- Editing a Plugin creates a new Plugin Revision that no Channel uses until it is explicitly moved to it. Moving a Channel creates a new Channel Revision and re-validates the Binding's config against the new schema. The Web App and CLI offer this as one action across selected Channels.

Ownership (on the Plugin) is about scoping and access; creation (on the Plugin Revision) is provenance only.

Plugin editing: amended by ADR 0024. Edits happen in disposable Plugin Drafts; promotion
creates a new permanent Revision with the Draft's parent Revision and makes it current.
Selecting any prior Revision as current is also allowed. Neither operation moves Bindings.

## Alternatives rejected

- **Config on the Plugin Revision (ADR 0016 as written).** Makes a Plugin single-use and forces copies for every Channel.
- **Bindings follow the Plugin's current Revision.** Convenient, but an edit to a shared Plugin silently changes every Channel using it, and a schema change can invalidate stored config without notice.
- **Unversioned Channels.** Simpler, but a config edit would erase the record of what produced earlier Articles.

## Consequences

- A Channel Revision alone fully determines a Collection's code and config.
- Plugin changes need a deliberate upgrade step per Channel.
- Config schema changes surface as validation errors at upgrade time, not as failed Plugin Runs.
- Amends ADR 0016: Plugin Revisions no longer hold per-Channel config.
