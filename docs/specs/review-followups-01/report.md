# Code-complete report: review-followups-01-04, ship migrations inside the package

- **Covers:** `a13fabd..d352ef6` on branch `feat/design-consistency-pass`
- **Spec:** `docs/specs/review-followups-01/spec.md`
- **Tickets:** review-followups-01-04 (done). Earlier reports: ticket 01 at `01e4f81:docs/specs/review-followups-01/report.md`, ticket 03 at `d16e591:docs/specs/review-followups-01/report.md`, and ticket 02 at `a13fabd:docs/specs/review-followups-01/report.md`. Tickets 05 and 06 are open and are **not** covered here.
- **Sync:** n/a (no `external:` links)
- **Date:** 2026-10-17

## Verdict
**CODE COMPLETE** (ticket 01-04 only): the tests assert AC-6, AC-7 and AC-8, every Config cleanup item is done, all three axes pass, and all the gates are green. Every finding is minor.

The spec as a whole is not code complete until tickets 05 and 06 are done and reviewed.

## Findings
There are no blockers or majors. The minor findings are below.

### Standards
- [minor] `src/news/migrations/env.py:29-33`. Source: baseline §6, minimal scope ("The diff matches the ticket … no drive-by changes").
  - The new `try/finally: engine.dispose()` around the developer CLI fallback is not in the ticket's Goal or Verification.
  - It is justified: without it, the AC-8 test raises a `ResourceWarning`. The Spec reviewer accepted it on that basis.
  - Fix: mention it in evidence/04.md or the PR description.
- [minor, already there before this ticket] `src/news/migrations/env.py:28`. Source: baseline §5 ("Every failure mode is either handled deliberately or fails loudly, and is logged with context").
  - `os.environ["NEWS_DATABASE_URL"]` raises a bare `KeyError` on the developer `alembic` path when the variable is unset. It fails loudly, but without context.
  - Fix (later ticket): raise an error that names the variable and says the root `alembic.ini` is for developer use.

### Spec
- [minor] `tests/service/test_migrations.py:42-60`. Source: AC-8, "From the repository root, Alembic's `check` command, run through the root `alembic.ini` …".
  - Neither AC-8 test sets the working directory, so both depend on pytest being started from the repo root. They pass today because `news:migrations` resolves the same way from any directory.
  - Fix: add `monkeypatch.chdir(REPO_ROOT)` to both tests.
- [minor] `tests/service/test_migrations.py:31`. Source: AC-7, "upgrades a fresh SQLite database to head".
  - The expected head comes from `ScriptDirectory.from_config(alembic_config())`, the same config the code under test uses, so a wrong `script_location` would agree with itself. The `is not None` check and the AC-6 wheel test reduce this risk.
  - Fix (optional): also assert the known revision `d2ebcc45139c`, or build the `ScriptDirectory` from the package path.
- [minor] `docs/standards.md:129`. Source: ticket Verification, "Config cleanup".
  - The heading changed from `alembic/**` to `alembic.ini`. That isn't on the cleanup list, but it keeps the file consistent with the D-5 glob change.
  - Fix: none needed. Mention it in the PR description.

### Code-complete evidence
- [minor] `docs/specs/review-followups-01/evidence/04.md:79-84`. Source: code-complete item 7.
  - The evidence has a "Local smoke" note but no explicit Not verified list and no deployment item of its own. The same finding came up on evidence 02.
  - Fix: none needed in the evidence. This report's Not verified section and checklist cover it.
- [minor] `tests/service/test_migrations.py:18-30`. Source: code-complete item 1 (test strength).
  - The AC-7 test runs against the editable install, so `news:migrations` resolves to `src/`. It proves the code no longer depends on the working directory, but not that an installed wheel can migrate.
  - The installed-wheel case is covered only by the AC-6 contents test and the informal smoke run. AC-7 as written is met.
  - Fix: none for code complete. "Clean venv" stays on the deployment checklist.

## Criteria evidence
| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| AC-6 | `tests/test_packaging.py::test_wheel_contains_the_migrations` | yes: real `uv build --wheel` into `tmp_path`, exactly one wheel, exact `news/migrations/env.py`, at least one `news/migrations/versions/*.py` | n/a: no inputs (justified in evidence) | n/a: no inputs | n/a | yes: AssertionError listing a wheel without `env.py` | yes |
| AC-7 | `tests/service/test_migrations.py::test_migrate_reaches_head_outside_the_repository`; the existing `tests/service/test_schema.py` (8 tests, including the downgrade, which now uses `alembic_config()`) | yes: `chdir(tmp_path)`, fresh SQLite file, revision equals script head | n/a: no new failure paths (justified) | yes: working directory outside the repo | n/a | yes: `CommandError: Path doesn't exist: …/alembic` after the `git mv` (honestly recorded that it first passed on the old layout) | yes |
| AC-8 | `test_root_alembic_ini_finds_no_differences_from_the_models`, `test_root_alembic_ini_reports_a_schema_the_models_do_not_describe` | yes: `command.check(Config(REPO_ROOT / "alembic.ini"))` against a migrated temporary database | yes: a stray table raises `AutogenerateDiffsDetected` matching "stray", so the happy test isn't vacuous | n/a | n/a | yes: same `CommandError`; drift test's sanity inversion recorded ("DID NOT RAISE") | yes |
| Config cleanup | grep and diff: `ALEMBIC_INI` and `parents[3]` gone; ruff `known-third-party` removed; pyright `include = ["src", "tests"]`; core glob `alembic.ini` in `docs/mobua-swe.md` | yes | n/a | n/a | n/a | n/a: config | yes: lint and typecheck green |

From commit history:
- The tests landed with their code in f033bc0, which meets "before or with".
- In 1adf2ec, the only test change is import order in `test_migrations.py`, which follows from dropping ruff's `known-third-party`.
- No tests were deleted, weakened or skipped. There is no `skip` or `xfail` anywhere in `tests/`.

Mocks and seams: there are no mocks. The wheel build is a real `uv build`. Alembic runs real `upgrade`, `check` and `downgrade`. SQLite uses real files in `tmp_path`. Each boundary has a real integration test.

## Gates
| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass (0 errors) |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass (114 files formatted, 1 contract kept) |
| Full suite | `uv run pytest` | pass (115 tests, none skipped) |
| Build | `uv build` | pass. The wheel has `news/migrations/env.py`, `script.py.mako` and the `d2ebcc45139c` revision; the sdist has them under `src/news/migrations/`. |

## Observability delivered
- **Logs:** none. The ticket says "None. This is packaging only." Alembic's errors propagate unchanged, and the only new code path, `engine.dispose()` in a `finally`, is not a failure path.
- **Metrics:** none, as the spec requires (D-15).

## Not verified
Code complete is not deployment verified. This review did **not** verify:
- Deployment, runtime behavior in the target environment, or real traffic and data.
- `news db upgrade` from an installed wheel, except one informal smoke run on the author's macOS machine (fresh 3.14 venv outside the repo: "Database is up to date.", exit 0, `alembic_version` = `d2ebcc45139c`). The tests use the editable install.
- Anything in a container image, which is out of scope for this ticket.
- Anything on Postgres, which is out of scope for this ticket.
- The developer `alembic` CLI run by hand through the root `alembic.ini`. It is covered by tests only.
- Anything in tickets 05 and 06.

## Deployment verification checklist
Check these by hand or in the observability system, to confirm the deployed change does what the spec and ticket intend.

- [ ] **Clean venv:** `uv build`, then `pip install dist/*.whl` into a fresh venv outside the repo, then `news --database-url sqlite:///x.db db upgrade`.
  - It succeeds without a source checkout.
  - `sqlite3 x.db "select version_num from alembic_version"` returns `d2ebcc45139c`.
  - Running `db upgrade` again prints `Database is up to date.` and exits 0.
- [ ] **Clean venv, CLI checks:** from the same venv, the ticket-02 checks (`a13fabd:docs/specs/review-followups-01/report.md`) give the same results as from a source checkout.
- [ ] **Developer path:** from the repo root, with `NEWS_DATABASE_URL` pointing at a migrated database, `uv run alembic check` reports `No new upgrade operations detected.`
