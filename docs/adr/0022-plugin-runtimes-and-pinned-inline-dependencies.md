# 0022. v1 Plugins run on Python or shell, with pinned inline dependencies run by uv

Status: Accepted
Date: 2026-10-16
Amends: ADRs 0005, 0011

## Context

ADR 0005 lets Plugins be written in any language, but a Plugin only runs if its runtime is in the container, and ADR 0011 deliberately avoids shipping a second runtime such as Node. Plugin code is stored as data and materialized into a temporary directory per run (ADR 0016), so nothing says where a Plugin's third-party dependencies come from. Plugin Revisions are immutable (ADR 0018), so the same Revision should always run the same code.

## Decision

- **Runtimes.** The v1 image ships Python and a POSIX shell. A Plugin may use any runtime present in the image; adding another (e.g. Node) is a deliberate image change, not an implied promise.
- **Dependencies.** Python Plugins declare dependencies inline with standard script metadata (PEP 723), and the Channel runs them with `uv run`, which resolves and caches them. The cache belongs to the Plugin OS user (ADR 0020).
- **Reproducibility.** Inline dependencies must be pinned exactly (`==`). Validating a Plugin Revision rejects unpinned dependencies.
- **Network.** The first run of a new Revision needs package-index access, which Plugins already have (ADR 0020).

## Alternatives rejected

- **Requirements file plus a virtualenv per Plugin Revision.** Same outcome with more machinery to build, store, and clean up.
- **Any language, runtimes installed on demand.** Keeps ADR 0005's promise literally, but bloats the image or makes runs depend on ad hoc installs.
- **No third-party dependencies.** Simplest, but rules out ordinary scraping and parsing libraries.

## Consequences

- One mechanism covers Built-in and Reader-written Python Plugins, including the RSS Built-in Plugin.
- A Plugin Revision plus the uv cache fully determines what runs; upgrading a dependency means a new Plugin Revision.
- Supporting another language later means adding its runtime and a dependency story for it, in a new ADR.
- Narrows ADR 0005 ("any language") and ADR 0011's consequence ("Plugins can be any language").
