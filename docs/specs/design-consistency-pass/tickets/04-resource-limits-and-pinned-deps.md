---
id: design-consistency-pass-04
title: Plugin Run resource limits and pinned PEP 723 dependencies via uv
status: todo
blocked_by: [design-consistency-pass-03]
external: null
---

# Plugin Run resource limits and pinned PEP 723 dependencies via uv

## Goal
Apply CPU-time, memory, and file-size limits to Plugin Runs, validate that Python Plugin Revisions pin inline (PEP 723) dependencies exactly, and launch Python Plugins with `uv run` using a cache owned by the Plugin OS user.

## Criteria covered
AC-13, AC-49, AC-50

## Seams
- Pure core: PEP 723 metadata parsing and exact-pin check; limit configuration.
- Edge: launcher applies rlimits and invokes `uv run`; integration test in the container image against a local package index or pre-seeded cache.

## Observability
- Extends `plugin_run.failed` with the limit that was hit.

## Verification
- AC-13: tests exceeding each of memory (512 MiB default), CPU time (300 s default, use a low configured value in tests), file size (100 MiB default) are killed and recorded with the limit.
- AC-49: `feedparser>=6` rejected; `feedparser==6.0.11` accepted; no metadata accepted (no deps).
- AC-50: pinned Plugin runs via `uv run`, cache written only under the Plugin user's cache dir.

## Out of scope
- Runtimes other than Python and shell.
- Dependency upgrade tooling.
- Built-in RSS Plugin (ticket 05).
