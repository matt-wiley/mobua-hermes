# Fix report: Validate ADR index rows without a leading pipe

- **Covers:** `76aadba..e92564886b7089a2ea1a32811d8ca74766d08d1d` on `feat/docs-postgres-ci`.
- **Spec:** `docs/specs/design-consistency-pass/spec.md`, AC-56.
- **Ticket:** `design-consistency-pass-21`; the major finding from the review of `9de31c8`.
- **Sync:** local only (`external: null`); no external tracker writes.
- **Date:** 2026-10-18.

## Verdict

**Fix implemented; independent review pending.** Rows without a leading pipe now reach
the existing duplicate, field, and malformed-row checks. All required local gates pass.
This repair does not upgrade the ticket's independent review verdict. Run
`/mobua-swe:code-review` in a fresh context to review it.

## Reproduction and root cause

Expected: adding a second ADR 0001 table row without a leading `|` reports the duplicate
and returns nonzero. Before the repair, `_table_rows` selected only lines starting with
`|`, silently discarded the duplicate, and returned success. Optional outer pipes are valid
[GitHub Flavored Markdown table syntax](https://github.github.com/gfm/#example-199), as
confirmed during the review.

The repair recognizes an ADR table by its header, a pipe-prefixed row, or an ADR link.
Subsequent pipe-delimited rows in that block are validated regardless of the leading pipe.
A blank line ends the block, so surrounding prose containing pipes remains ignored.
Separator recognition also accepts omitted outer pipes. Existing header recognition,
field validation, and diagnostic formatting are preserved.

Only `scripts/check_adrs.py` changes in production. No public interface, dependency,
configuration, migration, or ADR changes are needed.

## Criteria evidence

Detailed output and commit order: [evidence/21.md](evidence/21.md).

| Criterion / category | Tests | Result |
|---|---|---|
| Duplicate failure and optional trailing-pipe edge | `test_a_duplicate_row_without_a_leading_pipe_is_a_problem` (2 cases) | exact duplicate diagnostic |
| Unknown ADR and malformed-row failures | `test_invalid_rows_without_a_leading_pipe_are_reported` (2 cases) | exact diagnostics |
| Valid rows; header-present/header-absent boundary | `test_consistent_index_rows_can_omit_leading_pipes` (2 cases) | no problems |
| Surrounding prose boundary | `test_prose_with_pipes_outside_the_index_table_is_ignored` | no problems |
| Filesystem visibility and exit status | `test_the_script_reports_a_duplicate_without_a_leading_pipe` | exit 1, exact stderr, no success output |

Red before production changes: **7 failed, 48 passed in 0.13s**. Failures showed missing
validation or a false success, with no syntax/import errors. Tests were committed first
in `92e9795`; production followed in `e925648`. Green: **55 passed in 0.05s**.

The original review reproduction was also repeated on a temporary copy of the real
26-ADR directory. Appending ADR 0001 without a leading pipe now prints
`<temporary directory>/README.md: 0001: listed 2 times` and returns `1`.

Existing empty/missing-index, metadata, amendment, field, and first-row regressions all
remain green. No existing tests were deleted, weakened, skipped, or mocked. Numeric
ranges do not apply to this text-formatting defect.

## Gates

Run after the production repair, before documentation-only updates:

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors, warnings, informations |
| Lint | `uv run ruff check .` | pass |
| Formatting | `uv run ruff format --check .` | pass: 177 files already formatted |
| Import boundaries | `uv run lint-imports` | pass: 1 kept, 0 broken |
| Full SQLite suite | `uv run pytest` | pass: 481 tests in 11.42 s |
| Current ADRs | `uv run python -m scripts.check_adrs docs/adr` | pass: 26 ADRs and index consistent |
| Diff whitespace | `git diff --check` | pass |

## Observability delivered

Previously ignored rows now reach the existing file/field diagnostics on stderr and
nonzero exit path. A real-filesystem regression asserts the exact duplicate message,
return value, and empty stdout. No new application events or metrics are appropriate:
ticket 21 explicitly requires checker diagnostics and named CI gates instead.

## Adjacent finding

An exploratory test exposed a separate existing `_parse_row` limitation: `strip("|")`
removes significant delimiters from compact rows ending with an empty cell, such as
`|[0002](0002-allow-postgres.md)|Allow Postgres|Accepted||`. Those rows are rejected rather
than silently accepted. Full removal of outer pipes with an empty final cell also needs
separate normalization work. These cases were excluded from this narrow repair before
production changes; the exploratory and committed failing-run counts are recorded in
the evidence. Follow up separately rather than expanding the leading-row-selection fix.

## Not verified

Code complete is not deployment verified. This repair has not received an independent
review. Hosted GitHub Actions and deployed-commit behavior remain unobserved. Postgres
and actionlint were not rerun for this parser-only change; their passing results in the
preceding review are historical validation. The accepted AC-59 test-order exception is
unchanged and is not used for this repair.

## Deployment verification checklist

- [ ] On the deployed commit, run `uv run python -m scripts.check_adrs docs/adr`: exit 0 and all ADRs/index consistent.
- [ ] In a test PR, append a duplicate ADR table row without its leading pipe: the hosted docs check fails, identifies the duplicate ADR number, and prints no success summary.
- [ ] Restore the index, including a valid row without its leading pipe: the hosted docs check passes.
