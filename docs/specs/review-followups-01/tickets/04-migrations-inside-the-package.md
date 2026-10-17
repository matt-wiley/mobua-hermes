---
id: review-followups-01-04
title: Ship migrations inside the package
status: todo
blocked_by: []
external: null
---

# Ship migrations inside the package

## Goal
Move `alembic/` to `src/news/migrations/` (`script_location = news:migrations`), so that `news db upgrade` works from an installed wheel. `migrate()` builds its config in code. The root `alembic.ini` stays only for developer autogenerate.

## Criteria covered
AC-6, AC-7, AC-8

## Seams
- **Edge:** `migrate()` in `service/db.py` with a code-built Alembic `Config`. Test it on SQLite with `monkeypatch.chdir(tmp_path)`.
- **Wheel check:** `uv build --wheel --out-dir <tmp_path>`, then inspect the zip. This is the one slower integration test.
- **Developer path:** run Alembic's `check` command through the root `alembic.ini` against a migrated temporary database.

## Observability
- None. This is packaging only.

## Verification
- **AC-6:** the wheel contains `news/migrations/env.py` and at least one `news/migrations/versions/*.py`.
- **AC-7:** with the working directory outside the repo, `migrate()` reaches head. The existing schema tests still pass.
- **AC-8:** `check` reports no new upgrade operations.
- **Config cleanup:**
  - remove `ALEMBIC_INI` and `parents[3]`;
  - remove ruff's `known-third-party = ["alembic"]` if it is no longer needed;
  - update pyright `include`;
  - change the core module glob in `docs/mobua-swe.md` from `alembic/**` to `alembic.ini`.
- **Feeds deployment check:** "Clean venv … `news … db upgrade`".

## Out of scope
- Schema changes, including the scope declarations (ticket 05).
- Container image changes.
- Postgres runs.
