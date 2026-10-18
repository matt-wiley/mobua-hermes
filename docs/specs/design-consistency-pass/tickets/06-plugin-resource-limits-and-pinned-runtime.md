---
id: design-consistency-pass-06
title: "Plugin resource limits and pinned Python runtime"
status: todo
blocked_by: [design-consistency-pass-05]
external: null
---

# Plugin resource limits and pinned Python runtime

## Goal
Apply CPU, memory, and file-size limits to the shared process runner and run pinned Python Plugins through uv with its cache owned by the Plugin user.

## Criteria covered
AC-13, AC-50

## Seams
- Pure core: limit configuration and runner command selection, reusing exact-pin validation delivered in 04.
- Edge: rlimits, uv invocation/cache permissions, subprocess-tree limit termination. Container integration uses a local package index or preseeded cache.

## Observability
- Extend normal plugin_run.failed with the limit hit. The reusable runner returns typed failures; later Draft tests display them without normal run logs/Health.

## Verification
- AC-13: each configured CPU, memory, and file-size limit terminates normal execution and creates normal Channel Health with the reason.
- AC-50: exact-pinned Python runs via uv; cache belongs to the Plugin user. No unpinned source gets past shared validation.
- Verify the same runner options can be selected by Draft orchestration without introducing durable run state.

## Deployment verification
- Own resource-limit and uv process/cache assertions supporting the normal Collection and later Test Run deployment checks.

## Out of scope
- Do not move exact-pin validation back behind the runner; 04 already owns AC-49.
- Other runtimes, dependency upgrade tooling, Built-in update delivery, Draft surfaces.
