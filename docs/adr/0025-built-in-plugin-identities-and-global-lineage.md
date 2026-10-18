# 0025. Built-in Plugins preserve global identities and development lineage

Status: Accepted
Date: 2026-10-17
Amends: ADRs 0019, 0024

## Context

Built-in Plugins evolve during development of the app and ship to many deployments.
Generating identities or ancestry independently in each deployment would obscure which
implementation is installed and invent a history unrelated to that development lifecycle.
Bundling every historical implementation would also grow release packages unnecessarily.

## Decision

- Built-in Plugins and their Revisions have stable UUIDs assigned during app development.
  Preserve those identities across releases and deployments.
- A Built-in's Revision lineage is global over the app's development lifetime. Deployments
  retain that lineage rather than manufacturing local ancestry.
- Built-ins have a different development lifecycle from Reader-owned Plugins. They need
  no deployment-generated starter root or local Draft/Promote simulation. This replaces
  ADR 0024's earlier application of the Reader creation flow to Built-ins.
- A release may ship only the latest Built-in implementations. Historical Revision code
  does not have to be bundled solely to reconstruct a local development history.
- Show only the Built-in history available locally. Do not bundle additional history
  metadata, create placeholder history entries, or fetch and expose unavailable ancestry.
  Preserve the global identities and lineage of installed Revisions without requiring
  every ancestor implementation to exist in the local database.
- Existing deployments retain the Built-in Revisions they already have. Future patch
  updates can add globally identified Revisions without rewriting those identities or
  ancestry. Reader-owned Revisions remain permanent under ADR 0024.
- Built-ins remain system-owned and read-only to Readers. Channel Bindings remain pinned
  to exact available Revisions. Eject still creates an independent Reader-owned Plugin
  under ADR 0024's Reader creation rules.
- Design of release/patch update delivery, installation, rollback, and other update
  mechanics is explicitly deferred to much later work.

## Alternatives rejected

- **Deployment-generated Built-in Revision UUIDs.** Lose a shared identity for the same
  implementation across deployments.
- **Simulating Reader Draft/Promote lineage locally.** Invents ancestry and couples two
  different development lifecycles without a requirement.
- **Bundling every historical implementation.** Increases release size unnecessarily.
- **Bundling a complete metadata-only history.** Exposes history the deployment cannot
  use and provides no required benefit.
- **Designing the update mechanism now.** Expands the Plugin Draft workflow beyond its scope.

## Consequences

- Built-in ancestry can refer to Revisions whose implementations are absent locally;
  history display is limited to locally available Revisions.
- A new deployment's available Revision set can differ from an older deployment's while
  shared Revisions retain the same UUIDs and ancestry.
- Persistence must support global Built-in identities and lineage without assuming the
  Reader-owned Plugin creation lifecycle.
