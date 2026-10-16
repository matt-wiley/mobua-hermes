# 0004. News Items use the app's own RSS-shaped schema

Status: Accepted
Date: 2026-10-16

## Context

Every Plugin must hand News Items to its Channel. The format could be literal RSS/Atom or a schema defined by the app.

## Decision

News Items use the app's own schema, modeled on RSS: a required stable id, title, link, published time, summary, full content, Source References, and free-form metadata. The id is the Feed's dedup key.

## Alternatives rejected

- **Literal RSS/Atom XML.** Familiar and tool-friendly, but has no reliable dedup key for scraped or searched content and handles full-text content poorly.

## Consequences

- RSS-based Plugins map feed entries into the schema.
- Every Plugin is responsible for producing a stable id.
- Changing the schema later affects every Plugin.
