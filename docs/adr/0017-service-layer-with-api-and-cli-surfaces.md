# 0017. One Python package: a service layer with API and CLI surfaces

Status: Accepted
Date: 2026-10-16

## Context

Before the Web App exists, Readers need a way to create Channels and Plugins, and the Web App will need an API later.

## Decision

One Python package with three layers:

```
src/news/
  service/   # domain logic: Channels, Revisions, Collection, Publish, scheduler, LLM Gateway
  api/       # FastAPI routes, thin wrappers over service/
  cli/       # Typer commands, thin wrappers over service/
web/         # SvelteKit project, built to static assets served by api/
```

`api/` and `cli/` may import `service/`, never each other; `service/` imports neither. This is enforced in CI (e.g. import-linter). The CLI runs in-process: it imports the service layer and opens the same database directly. Only the server process runs the scheduler. SQLite runs in WAL mode so the CLI and server can share it. A remote CLI mode over the API may come later.

## Alternatives rejected

- **Separate subprojects (e.g. uv workspaces).** Clean boundaries, but versioning and packaging overhead before any surface needs to ship separately.
- **CLI as an API client only.** Requires a running server and auth for basic local admin.

## Consequences

- The Web App is just another API client; work done before it exists isn't thrown away.
- Layering depends on the import rule being enforced.
