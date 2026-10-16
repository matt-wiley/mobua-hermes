# 0013. SQLite by default, Postgres-ready, one shared database

Status: Accepted
Date: 2026-10-16

## Context

The app must run locally with zero setup (ADR 0006) and scale to bigger deployments and multiple Readers (ADR 0007). Channels own their history (ADR 0003).

## Decision

Use SQLite by default, as a single file on the data volume, accessed through SQLAlchemy with Alembic migrations. Keep everything Postgres-compatible so a larger deployment only changes the connection string. All Channels share one database; Channel ownership is logical, with every row scoped by Reader, and by Channel where the row belongs to one (ADR 0007).

## Alternatives rejected

- **Postgres only.** Production-grade from the start, but adds a second service to every local run.
- **One database per Channel.** Physically matches Channel ownership, but complicates migrations, Aggregation, and backups.

## Consequences

- No SQLite-only or Postgres-only SQL features without a fallback.
- SQLite's single-writer limit may pinch with many concurrent Collections; that's the signal to move to Postgres.
- Channel isolation is enforced in code, not by the database.
