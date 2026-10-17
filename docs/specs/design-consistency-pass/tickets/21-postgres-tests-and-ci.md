---
id: design-consistency-pass-21
title: Postgres repository tests and a CI workflow for core
status: todo
blocked_by: [design-consistency-pass-01, design-consistency-pass-19]
external: null
---

# Postgres repository tests and a CI workflow for core

## Goal
Make the SQLite/Postgres portability rule checked rather than promised, and run the core gates and the docs check on every pull request instead of only in local and agent runs.

## Criteria covered
AC-58, AC-59

## Seams
- Test fixture: the repository and schema tests take their engine from `NEWS_TEST_DATABASE_URL`, defaulting to SQLite. Alembic migrations run against whichever database is chosen. psycopg 3 is a dev dependency (`docs/standards.md`).
- `.github/workflows/core.yml`: uv setup with the pinned Python, then the `docs/mobua-swe.md` core commands for typecheck, lint and `test_all`, a Postgres service container job running the repository tests, and the AC-56 docs check.
- Actions pinned to full commit SHAs, and the Postgres image pinned to an exact version.

## Observability
- None in the app. A failing CI step is the signal, and the step names are what shows up in the PR checks.

## Verification
- AC-58: run the repository and schema tests locally with `NEWS_TEST_DATABASE_URL` pointed at a Postgres container: they pass. Unset, they run on SQLite. A deliberately Postgres-incompatible construct in a scratch test fails on Postgres (red), confirming the run really uses Postgres.
- AC-59: the workflow file passes `actionlint`. The first PR after this ticket shows each step as a separate check. Breaking the ADR index on a scratch branch fails the docs-check step.
- Deployment checklist: "Open a PR and confirm the core CI workflow runs every step and passes. A branch with a broken ADR index fails the docs-check step."

## Out of scope
- Web module CI (no web code yet).
- Running the container-image integration tests (tickets 03, 04 and 20) in CI. They stay a local `docker` run for now.
- Branch protection or required-check settings on GitHub. Those are the repo owner's call.
- Building or publishing the container image.
