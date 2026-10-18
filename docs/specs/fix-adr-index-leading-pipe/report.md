# Code-complete report: ADR index rows without a leading pipe

- **Covers:** `76aadba..a3709f177590c5a0ea1c1a07d20aa2ec64bf1b17` on branch `feat/docs-postgres-ci`.
- **Spec:** `docs/specs/design-consistency-pass/spec.md`, AC-56.
- **Ticket:** `design-consistency-pass-21` (`status: done`); this review assesses only the latest parser repair, not the entire ticket or branch.
- **Sync:** not applicable (`external: null`); no external tracker writes.
- **Date:** 2026-10-18.

## Verdict

**NOT CODE COMPLETE**: the leading-pipe repair passes its regressions and all required
local gates, but introduces a table-boundary regression that rejects a valid ADR index.
Standards and Spec fail; Code-complete evidence passes for the recorded repair.

Three fresh-context reviewers assessed Standards, Spec, and Code-complete evidence.
The review did not change production code or tests, squash commits, or push.

## Findings

### Standards

- **[major] `scripts/check_adrs.py:175` — Table state survives a Markdown block boundary.**
  `_table_rows` clears `in_table` only on an empty line. After a heading immediately
  following the ADR table, subsequent prose containing `|` is collected as an index row.
  An index that lists every ADR exactly once with matching fields then fails the docs
  gate. Source: baseline standards section 3 requires boundary and edge-case coverage;
  `test_prose_with_pipes_outside_the_index_table_is_ignored` at
  `tests/scripts/test_check_adrs.py:261` exercises only blank-line boundaries.
  [GFM example 201](https://github.github.com/gfm/#example-201) confirms that a new
  block-level structure also terminates a table. **Fix:** terminate table state at
  Markdown block boundaries before collecting further pipe-containing text, with
  failing-first heading and block quote regressions that preserve omitted-leading-pipe
  validation. Use `/mobua-swe:fix` for this narrow follow-up.

Readability, Python idioms, pure parsing/filesystem separation, explicit diagnostics,
and production scope otherwise pass. Installed Python 3.14.6, FastAPI 0.143.3,
SQLAlchemy 2.1.5, Alembic 1.20.0, Typer 0.27.3, and Pydantic 2.14.1 remain on the
major versions recorded by the repository configuration and standards snapshot.

### Spec

- **[major] `scripts/check_adrs.py:175` — Same boundary regression as above.**
  AC-56 (`docs/specs/design-consistency-pass/spec.md:250`) requires checking that the
  index lists every ADR exactly once with matching title, status, and Amended-by fields.
  The reproduced input satisfies those conditions but fails because unrelated prose
  becomes a malformed row. Both heading and block quote boundaries were reproduced.
  This is one defect shared by both review axes, not two separate findings.

The omitted-leading-pipe duplicate, unknown-row, malformed-row, and valid-row behavior
is verified by reading the tests. No ADR contradiction or excess production scope was
found. Ticket 21's observability requirement is met by precise stderr diagnostics and
nonzero exit, with no new application events or metrics.

### Code-complete evidence

No additional findings. All required gates were rerun successfully. History confirms
`92e9795` adds only tests (61 additions, no deletions), followed by production-only
`e925648`. An independent in-memory replay of the 55 current ADR tests against the
`76aadba` parser reproduced **7 failed, 48 passed in 0.09 s**, corroborating the recorded
red run. Failures concern the missing behavior, not syntax or import errors.

No pre-existing tests were deleted, weakened, skipped, or mocked. Real temporary-file
tests cover the filesystem boundary and exact diagnostics. Numeric ranges and
application metrics are inapplicable to this text parser. The concrete deployment
checklist remains unverified. The new block-boundary case above still needs its own
failing-first regression and repair before another review can pass.

## Reproduction of the new finding

Using the existing test fixtures, without editing any file:

```sh
.venv/bin/python - <<'PY'
import runpy
from scripts.check_adrs import check

fixtures = runpy.run_path("tests/scripts/test_check_adrs.py")
index = fixtures["CONSISTENT_INDEX"] + "## Notes\nUse a pipe | to separate cells.\n"
print(check(fixtures["CONSISTENT_FILES"], index))
PY
```

Reviewed head:

```text
["README.md: row: 'Use a pipe | to separate cells.' does not have 4 cells"]
```

The same fixtures and input passed to the parser loaded from `76aadba` return `[]`.
This confirms an introduced false failure rather than the known normalization issue.

## Criteria evidence

Historical red/green output: [evidence/21.md](evidence/21.md).

| Criterion / behavior | Tests | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| AC-56: duplicate without leading pipe | `test_a_duplicate_row_without_a_leading_pipe_is_a_problem` (2 cases) | n/a: rejection | yes | leading pipe omitted | trailing pipe present/absent | yes | yes |
| AC-56: invalid rows without leading pipe | `test_invalid_rows_without_a_leading_pipe_are_reported` (2 cases) | n/a: rejection | unknown ADR, malformed row | leading pipe omitted | exact diagnostics | yes | yes |
| AC-56: valid rows without leading pipes | `test_consistent_index_rows_can_omit_leading_pipes` (2 cases) | yes | covered above | header present/absent | separator without outer pipes | yes | yes |
| AC-56: surrounding prose | `test_prose_with_pipes_outside_the_index_table_is_ignored` | yes | n/a: valid input | blank lines only | pipe in prose | already passed at base | yes, but block boundary is missing |
| AC-56: filesystem diagnostics and exit | `test_the_script_reports_a_duplicate_without_a_leading_pipe` | n/a: rejection | exit 1, exact stderr | real temporary files | empty stdout | yes | yes |
| AC-56: existing index checks | `test_an_adr_missing_from_the_index_is_a_problem`, `test_an_adr_listed_twice_is_a_problem`, `test_a_row_whose_title_differs_is_a_problem`, `test_a_row_whose_status_differs_is_a_problem`, `test_a_row_whose_amended_by_differs_is_a_problem`, first-row regressions, `test_the_repository_adrs_pass` | yes | yes | missing/header-absent inputs | field/link mismatches | historical; unchanged | yes |
| AC-56: heading/block quote ends table | review reproduction above | **fails** | false malformed-row diagnostic | block boundary without blank line | pipe in following prose | reproduced during review; no committed test | **no** |

AC-55's unchanged metadata/amendment tests remain green. AC-58, AC-59, and the carried
Postgres promotion check are outside this parser-only review; their historical results
and the accepted AC-59 test-order exception are unchanged. That exception is not used
for this repair, which followed test-first order.

## Gates

Independently rerun against the reviewed head:

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors, warnings, informations |
| Lint | `uv run ruff check .` | pass |
| Formatting | `uv run ruff format --check .` | pass: 179 files already formatted |
| Import boundaries | `uv run lint-imports` | pass: 1 kept, 0 broken |
| Full SQLite suite | `uv run pytest` | pass: 481 tests in 11.63 s |
| Focused ADR tests | `uv run pytest tests/scripts/test_check_adrs.py` | pass: 55 tests in 0.05 s |
| Current ADRs | `uv run python -m scripts.check_adrs docs/adr` | pass: 26 ADRs and index consistent |
| Diff whitespace | `git diff --check 76aadba..a3709f1` | pass |

Passing gates do not exercise the newly reproduced boundary case.

## Observability delivered

Previously ignored rows reach the existing file/field diagnostics on stderr and
nonzero exit path. The filesystem regression asserts the exact duplicate message,
return value, and empty stdout. No new application events or metrics are appropriate:
ticket 21 explicitly requires checker diagnostics and named CI gates instead.

## Adjacent finding retained from implementation

The pre-existing `_parse_row` normalization uses `strip("|")`, removing significant
delimiters from compact rows ending with an empty cell, for example
`|[0002](0002-allow-postgres.md)|Allow Postgres|Accepted||`. Full outer-pipe omission
with an empty final cell also needs separate normalization work. The exploratory
tests and their exclusion before production changes are disclosed in the evidence.
This unchanged limitation is separate from the introduced boundary regression and
is not charged as a new finding against this repair.

## Not verified

Code complete is not deployment verified. This review did **not** verify:

- A repair for the new block-boundary regression; production code and tests are unchanged.
- Hosted GitHub Actions or deployed-commit behavior with target-environment data.
- Postgres execution or actionlint in this parser-only review; preceding results are historical.
- Branch protection, web CI, hosted container integration tests, or image publishing,
  which are outside ticket 21.

## Deployment verification checklist

- [ ] On the deployed commit, run `uv run python -m scripts.check_adrs docs/adr`: exit 0 and all ADRs/index consistent.
- [ ] In a test PR, append a duplicate ADR table row without its leading pipe: the hosted docs check fails, identifies the duplicate ADR number, and prints no success summary.
- [ ] Restore the index, including a valid row without its leading pipe: the hosted docs check passes.
- [ ] After repairing the boundary regression, add a heading or block quote immediately after a valid table, with pipe-containing prose outside the table: the deployed checker and hosted docs check both pass.
