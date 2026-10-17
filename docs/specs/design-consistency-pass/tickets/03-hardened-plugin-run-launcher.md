---
id: design-consistency-pass-03
title: Hardened Plugin Run launcher and a manual Collection
status: todo
blocked_by: [design-consistency-pass-02]
external: null
---

# Hardened Plugin Run launcher and a manual Collection

## Goal
Run a Channel's Plugin Bindings as hardened subprocesses (clean env, Plugin OS user, per-run temp dir), buffer output and ingest only on exit 0, keep a capped stderr log, and record failures in Channel Health; triggered by a CLI `collect` command. Includes the container image with the Plugin OS user.

## Criteria covered
AC-11, AC-12, AC-14, AC-15, AC-16 (also verifies AC-23's Plugin Run environment part)

## Seams
- Pure core: environment allowlist builder; output buffer + ingest decision; stderr capping.
- Edge: a `PluginLauncher` interface; the real launcher (uid switch, env, temp dir) is integration-tested in the container image; service-layer tests use a fake launcher.
- Channel Health record (created here) and a CLI view of it.

## Observability
- `warning` `plugin_run.failed` (Channel id, Plugin Revision id, exit code, duration, log reference).
- `warning` `news_item.rejected` (Channel id, Plugin Run id, News Item id, reason).

## Verification
- AC-11: env-dump test Plugin shows only allowlisted basics, one declared Secret, Gateway URL and Token (Gateway Token may be a placeholder value until ticket 10).
- AC-12: uid is the Plugin user's; reading the DB file and Master Key file is denied.
- AC-14: two concurrent runs cannot read each other's temp dirs.
- AC-15: exit 0 ingests 5; exit 1 ingests 0; timeout kill ingests 0.
- AC-16: stderr over 1 MiB is truncated and marked; failed run's Health entry links the log.
- AC-23 (env part): sentinel provider key never appears in a Plugin Run's environment.
- Deployment checklist: "Run the env-dump test Plugin: its log shows no Master Key or provider key variables."

## Out of scope
- CPU/memory/file-size limits and `uv run` dependencies (ticket 04).
- Scheduling Collections (ticket 16).
- Real Gateway Tokens and LLM turns (ticket 10).
- Built-in Plugins (ticket 05).
