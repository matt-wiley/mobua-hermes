---
version: 1
tracker:
  system: github
  connector: gh               # GitHub CLI, repo matt-wiley/mobua-hermes
  authority: external-for-status-assignee-priority; repo-for-detail-and-criteria
layout:
  specs: docs/specs
  adr: docs/adr
  context: CONTEXT.md
  standards: docs/standards.md
observability:
  logging: structlog (JSON to stdout)
  metrics: prometheus-client (/metrics)
  where_to_look: "`docker logs <container>`; GET /metrics; Channel Health in the Web App"
modules:
  - name: core
    glob: "{src/news/**,tests/**,alembic.ini,pyproject.toml,uv.lock}"
    language: python
    framework: fastapi
    versions: {python: "3.14", fastapi: "0.143", sqlalchemy: "2.1", alembic: "1.20", typer: "0.27", pydantic: "2.14"}
    standards: [python, fastapi, sqlalchemy]
    commands:
      build: "uv build"
      typecheck: "uv run pyright"
      lint: "uv run ruff check . && uv run ruff format --check . && uv run lint-imports"
      test_single: "uv run pytest {file}"
      test_all: "uv run pytest"
    commands_verified: true    # all five ran green on 2026-10-17 (53 tests)
  - name: web
    glob: "web/**"
    language: typescript
    framework: sveltekit
    versions: {typescript: "6", node: "24", sveltekit: "3.1", svelte: "5.57", vite: "8", vitest: "5", adapter-static: "4"}
    standards: [typescript, sveltekit]
    commands:
      build: "npm --prefix web run build"
      typecheck: "npm --prefix web run check"
      lint: "npm --prefix web run lint"
      test_single: "npm --prefix web exec -- vitest run {file}"
      test_all: "npm --prefix web test"
    commands_verified: false   # nothing to run yet: no web/package.json
---

# mobua-swe repo config

Written by `/mobua-swe:setup` on 2026-10-16 and updated on 2026-10-17. Every other skill reads this file and stops if it is missing or stale.
Skills pick the module from the files a ticket touches.

## Status

- **core: verified on 2026-10-17.** `src/news` was scaffolded by design-consistency-pass-01. On that date, all five commands ran and passed: build, typecheck (pyright strict), lint (ruff check, ruff format, lint-imports), a single test file, and the full suite (53 tests). Resolved versions: Python 3.14.6, FastAPI 0.143.3, SQLAlchemy 2.1.5, Alembic 1.20.0, Typer 0.27.3, Pydantic 2.14.1.
- **web: not yet verified.** There is no `web/package.json` yet, so the commands above are the planned toolchain, not checked results. Re-run `/mobua-swe:setup` right after the web module is scaffolded.

## Version notes

- Python 3.14 is chosen over 3.15, which was released 2026-10-09.
- TypeScript is held at 6 because SvelteKit 3.1, svelte-check and typescript-eslint don't support 7.0 yet. See `docs/standards.md`, "Repo overrides".
