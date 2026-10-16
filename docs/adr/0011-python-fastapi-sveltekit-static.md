# 0011. Python + FastAPI core; SvelteKit web app served by FastAPI

Status: Accepted
Date: 2026-10-16
Amended by: ADR 0022

## Context

The service layer, API, and CLI need one backend stack. The Web App needs a frontend. ADR 0006 requires a single container.

## Decision

The backend (service layer, API, CLI) is Python, with FastAPI for the API. The Web App is SvelteKit, built as static assets and served by FastAPI from the same container.

## Alternatives rejected

- **TypeScript backend.** One language end to end, but Python has the stronger scraping, ETL, and LLM ecosystem for Plugins and Channels.
- **SvelteKit running its own Node server.** Allows SSR and server routes, but adds a second runtime and process to the container.

## Consequences

- SvelteKit runs in static/SPA mode: no SSR or SvelteKit server routes; all server logic lives in FastAPI.
- Plugins can use any runtime present in the image; in v1 that is Python and a POSIX shell (ADR 0022).
