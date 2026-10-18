---
id: design-consistency-pass-05
title: "Hardened Plugin process runner and manual Collection"
status: todo
blocked_by: [design-consistency-pass-02, design-consistency-pass-04]
external: null
---

# Hardened Plugin process runner and manual Collection

## Goal
Run pinned Plugin Revisions as restricted subprocesses and expose manual Collection through the CLI. Include the container Plugin OS user, clean environment, private run directory, timeout, capped stderr, and successful-run-only ingestion with normal Channel Health.

## Criteria covered
AC-11, AC-12, AC-14, AC-15, AC-16, AC-23

## Seams
- Pure core: environment allowlist, output validation/ingest decision, capped stderr representation.
- Edge: process runner interface for materialized Manifest/code/config; subprocess uid, private temporary directory, timeout/process-tree cleanup, stdout/stderr collection.
- Keep durable Plugin Run/Health creation and ingestion in normal Collection orchestration, not inside the shared runner. Draft tests will reuse the runner without those side effects.
- Service tests use a fake runner boundary; real process and filesystem isolation tests run in the container. Reuse completed encrypted credential services for declared Secrets only.

## Observability
- warning plugin_run.failed and news_item.rejected for normal promoted execution; include ids, exit/timeout, duration, and capped log reference without credentials.
- Container CLI logging persists at /data/logs/cli.log. Server logs remain JSON on stdout.

## Verification
- AC-11/23: real env-dump receives allowlisted basics and one declared Secret; Master Key, Provider credential, and unrelated server variables are absent. Gateway access may remain a placeholder until 11.
- AC-12/14: Plugin uid cannot read data/Master Key or concurrent run directories.
- AC-15: successful output ingests five valid items; nonzero exit or timeout ingests zero; validate Source References and record rejected normal items.
- AC-16: stderr beyond 1 MiB is capped/marked; failed normal run Health links to its log.
- Run the starter from 03 through the real runner and confirm exit 0 and zero News Items.

## Deployment verification
- Own env-dump and process-user/clean-environment portions of the collection checklist; verify container CLI logs persist and server logs use stdout. RSS demonstration is owned by 07.

## Out of scope
- CPU/memory/file limits and uv dependencies (06). Real Gateway tokens (11). Draft Test Run surfaces (15-16), Built-ins (07), scheduling (19).
