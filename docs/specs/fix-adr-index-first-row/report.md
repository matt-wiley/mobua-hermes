# Fix report: Validate the first ADR index entry

- **Covers:** `7c9063e..f4af4b7826424b4f6ae58073c2817ae2913a6e9d` on `feat/docs-postgres-ci`.
- **Spec:** `docs/specs/design-consistency-pass/spec.md`, AC-56.
- **Ticket:** `design-consistency-pass-21`; the two major findings in its review of `45b8d93`.
- **Sync:** local only (`external: null`); no external tracker writes.
- **Date:** 2026-10-18.

## Verdict

**Both major findings addressed**: the parser defect is fixed and all local gates pass;
the user accepted the historical AC-59 test-first exception on 2026-10-18. This narrow parser
repair has red-first evidence and is ready for independent review with
`/mobua-swe:code-review` in a fresh context. No independent review of this repair is claimed.
The original ticket review verdict is not upgraded by this documentation update.

## Findings and disposition

- **Parser major corrected.** `_table_rows` assumed the first pipe-delimited row was a header
  and discarded it without checking. It now skips that row only when its trimmed cells are
  the actual column names (`#`, `Decision`, `Status`, `Amended by`). Other first rows reach
  the existing duplicate, field and malformed-row checks. Public interfaces are unchanged;
  one source file changed, with no new dependencies, configuration or migrations.
- **Historical evidence major closed by one-time user exception (2026-10-18).** Ticket 21
  evidence accurately records that the
  CI workflow preceded its contract test. A new run or code change cannot repair that order.
  The existing mutation run remains useful behavioral evidence, and `21746bf` includes tests
  with implementation, but neither establishes test-first development. The original
  disclosure is preserved. The user explicitly accepted this particular exception after
  the repair was completed. See [the exception record](../design-consistency-pass/evidence/21.md#accepted-exception-ac-59-test-first-order-2026-10-18)
  for the authorization, scope and limits. This applies only to the AC-59 workflow/test
  ordering in `21746bf`; all other TDD requirements remain in force. No workflow rewrite,
  rewritten history or retrospective claim of compliance was introduced.

## Reproduction and criteria evidence

Expected: every actual ADR index entry is checked, including one replacing the header;
duplicates or mismatches cause a diagnostic and nonzero exit. Actual before the repair:
the first entry could be silently ignored and the command could report success.

| Criterion | Tests | Categories |
|---|---|---|
| Validate every first entry | `test_an_entry_replacing_the_header_is_validated` (3 cases) | duplicate, unknown ADR and malformed first row |
| Check first-entry fields | `test_the_first_entry_without_a_header_has_its_fields_checked` (4 cases) | title, status, Amended-by and link mismatches; missing-header boundary |
| Preserve valid headers | `test_a_header_is_recognized_by_its_cells_despite_spacing`; existing consistent/empty-index tests | happy path, whitespace edge and empty boundary |
| Make silent failure visible | `test_the_script_reports_a_duplicate_in_place_of_the_index_header` | real filesystem edge, exact stderr, exit 1 and no success output |

Numeric ranges do not apply to this table parsing bug. Existing tests continue to cover
ordinary duplicate/missing rows, metadata/amendment consistency and the real repository ADRs.
No mocks, skips, weakened assertions or deleted tests were introduced.

### Red first

Before changing `scripts/check_adrs.py`, added nine cases and ran:

```text
$ uv run pytest tests/scripts/test_check_adrs.py
test_an_entry_replacing_the_header_is_validated:
E AssertionError: assert [] == ['README.md: 0001: listed 2 times']
test_the_script_reports_a_duplicate_in_place_of_the_index_header:
E AssertionError: assert 0 == 1
Captured stdout: 2 ADRs and index are consistent: <temporary directory>
8 failed, 39 passed in 0.21s
```

All eight failures concerned missing validation/diagnostics, not import or syntax errors.
The valid-header whitespace case already passed. The tests were committed as `eac2b2e`
before the production repair in `f4af4b7`.

### Green

```text
$ uv run pytest tests/scripts/test_check_adrs.py
47 passed in 0.07s
```

## Gates

Run after the repair, before documentation-only updates:

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors, warnings, informations |
| Lint | `uv run ruff check .` | pass |
| Formatting | `uv run ruff format --check .` | pass: 176 files already formatted |
| Import boundaries | `uv run lint-imports` | pass: 1 kept, 0 broken |
| Full SQLite suite | `uv run pytest` | pass: 473 tests in 11.39 s |
| Current ADRs | `uv run python -m scripts.check_adrs docs/adr` | pass: 26 ADRs and index consistent |

## Observability delivered

The existing discrepancy reporting now sees the formerly skipped entry. The new filesystem
test asserts `README.md: 0001: listed 2 times` on stderr, exit 1 and empty stdout. No app
logging or metrics are added: this is a local documentation check, and ticket 21 explicitly
requires diagnostic output rather than new app events or metrics.

## Not verified

Code complete is not deployment verified. This fix has not had an independent review, and
hosted CI/deployment execution is unobserved. Postgres, workflow YAML and application database
behavior are unchanged; the preceding review's 283-test Postgres result is historical
validation, not a new run for this repair. The accepted AC-59 historical TDD exception does
not waive independent review or hosted/deployment verification.

## Deployment verification checklist

- [ ] On the deployed commit, run `uv run python -m scripts.check_adrs docs/adr`: exit 0,
  with all ADRs and the index consistent.
- [ ] In a test PR, replace the ADR table header with a duplicate ADR row: the hosted docs
  check fails, reports the duplicate number and never reports a success summary.
- [ ] Restore the valid header: the hosted docs check passes.
