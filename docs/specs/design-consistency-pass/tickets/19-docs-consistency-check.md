---
id: design-consistency-pass-19
title: Docs consistency check for ADR metadata and index
status: todo
blocked_by: []
external: null
---

# Docs consistency check for ADR metadata and index

## Goal
Add a local script that verifies ADR metadata and the ADR index, exiting non-zero on any mismatch.

## Criteria covered
AC-55, AC-56

## Seams
- Pure core: parse ADR headers and the index table; compare.
- Edge: file system read; CLI entry (e.g. `uv run python scripts/check_adrs.py` or a `news` CLI dev command).

## Observability
- None.

## Verification
- AC-55: missing Status/Date fails; one-way Amends link fails.
- AC-56: missing, duplicate, or mismatched index row fails; current repo passes.
- Deployment checklist: "Run the docs consistency check (AC-56) on the deployed commit: exit 0."

## Out of scope
- Wiring into CI (deferred to the first CI setup).
- Glossary linting.
