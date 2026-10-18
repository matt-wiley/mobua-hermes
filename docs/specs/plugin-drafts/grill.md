---
slug: plugin-drafts
external: null
confirmed: false
spec_written: false
---
# Grill: Plugin drafts and test runs

Split from `docs/specs/review-followups-01/grill.md` (branch 14). Readers want to tinker with a Plugin in an uncommitted state, test-run it, and only then turn it into a Plugin Revision that Channels can use in scheduled runs. This amends ADR 0016 and ADR 0018 ("Editing a Plugin creates a new Plugin Revision") and the glossary's Revision entry ("Edits create new Revisions"). An ADR is expected.

Must land before design-consistency-pass-03 (the Plugin Run launcher).

## Branches
| # | Branch | Status | Decision |
|---|---|---|---|
| 1 | Shape of a draft | resolved | A separate mutable working copy per Plugin, distinct from Plugin Revisions. Promote validates it (Manifest, AC-49 pins) and creates an immutable Plugin Revision. Bindings reference only Revisions. Rejected: Revisions with a draft/promoted status (weakens immutability); editor-local drafts only (lost with browser storage, no cross-device). Decided 2026-10-17 in review-followups-01. |
| 2 | Vocabulary: the term for the working copy and the verb ("Publish" is taken by the Channel process; candidates: Promote) | unresolved | |
| 3 | Cardinality: one draft per Plugin, or per Reader per Plugin; does a new Plugin start as a draft only | unresolved | |
| 4 | Scope: Plugins only, or Channels too | unresolved | |
| 5 | Surfaces: service layer (required by ADR 0017), API, Web App; what the CLI offers (e.g. create-and-promote) | unresolved | |
| 6 | Test runs: hardened launcher, no ingest, output shown; Channel context for Channel Models, Secrets and budget; call records and attribution; logs | unresolved | |
| 7 | Built-in Plugins and Eject: no drafts on Built-ins; does Eject land in a draft or a Revision | unresolved | |
| 8 | Impact on design-consistency-pass tickets (03 launcher inputs, 06 Eject, 10 Gateway Tokens) and ACs (AC-2, AC-3, AC-8, AC-49) | unresolved | |
| 9 | ADR: amending 0016/0018 | unresolved | |
| 10 | Observability and deployment verification | unresolved | |

## Terms added to CONTEXT.md
- (none yet)
