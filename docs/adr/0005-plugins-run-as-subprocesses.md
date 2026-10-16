# 0005. Plugins run as subprocesses

Status: Accepted
Date: 2026-10-16
Amended by: ADR 0022

## Context

Channels must run Plugins written as config, Python, JavaScript, or anything else, and a Channel may have several Plugins.

## Decision

Each Plugin runs as a subprocess. The Channel launches it with its config, and the Plugin writes News Items as JSON lines to stdout. During a Collection, all of a Channel's Plugins run in parallel; the Collection is complete once every Plugin Run has ended (successfully or not) and the Channel has ingested the News Items of the successful runs. A Plugin Run's output is buffered and ingested only if it exits successfully; a failed run contributes nothing. Config-only Plugins (e.g. RSS) are built-in Plugins that take config.

Runtimes: amended by ADR 0022. v1 supports runtimes present in the image (Python and a POSIX shell); Python dependencies are pinned inline (PEP 723) and run with `uv run`.

## Alternatives rejected

- **In-process modules.** Faster and easier to debug, but ties Plugins to one language and gives no isolation from crashes or hangs.

## Consequences

- The Plugin contract is language-agnostic: config in, JSON lines out.
- Channels need process management: parallel runs, exit tracking, killing hung Plugins.
- Per-run process startup cost.
