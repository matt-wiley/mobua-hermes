# Fix report: Respect Markdown block boundaries in the ADR index

- **Covers:** `2a3ea8d..3a2f8d751f5b02d6ef3aa5fdb0c80d1307348280` on `feat/docs-postgres-ci`.
- **Spec:** `docs/specs/design-consistency-pass/spec.md`, AC-56.
- **Ticket:** `design-consistency-pass-21`; major finding in the independent review of `a3709f1`.
- **Sync:** not applicable (`external: null`); no external tracker writes.
- **Date:** 2026-10-18.

## Verdict

**Fix implemented; independent review pending.** Valid ADR indexes followed by another
Markdown block pass, while real duplicate and malformed rows retain their diagnostics.
All required local gates pass. This implementation report does not upgrade the earlier
independent review verdict; run `/mobua-swe:code-review` in a fresh context.

## Reproduction and root cause

Expected: a heading or block quote immediately after a valid ADR table ends the table,
so subsequent prose containing a pipe does not become an ADR row. Actual: `_table_rows`
reset its table state only on blank lines, rejected that prose as malformed, and returned
exit 1 for a valid index. The reproduction generalizes to lists, code, HTML and thematic
breaks. The [GFM table rule](https://github.github.com/gfm/#example-201) defines these
block boundaries independently of particular prose.

Tests committed in `c7d0a1c`, before the production change, reproduced **19 failures and
58 passes**. The failures are false malformed-row diagnostics and the CLI's wrong exit
status, not syntax/import errors. The root cause and both red runs are recorded in
[evidence/21.md](evidence/21.md).

## Repair

`scripts/check_adrs.py` uses `MarkdownIt("commonmark").enable("table")` to obtain block
boundaries. It selects top-level table/paragraph source ranges, resetting candidate row
state for each block. Paragraph ranges preserve diagnostics for headerless or malformed
tables that are not recognized as Markdown tables. Nested quotes/lists, fences, code and
HTML are not index entries. No application API or CLI interface changes.

Validation still reads the original source lines. Markdown renderers may pad missing
cells or discard excess cells; using rendered cells would hide malformed input. Line
splitting follows Markdown's LF/CRLF/CR line endings so source maps remain aligned.
The [parser documentation](https://markdown-it-py.readthedocs.io/en/latest/using.html#the-token-stream)
and [token API](https://markdown-it-py.readthedocs.io/en/latest/api/markdown_it.token.html)
describe the block tokens, nesting levels and source maps used by this repair.

`markdown-it-py>=4.2,<5` is a direct development dependency for repository tooling. The
locked 4.2.0 package was already installed transitively; no package version changed.
The user explicitly authorized skipping grill for this dependency/config scope change.

## Criteria evidence

| Reproduction criterion / category | Tests | Red / green |
|---|---|---|
| New blocks end the index without a blank line | `test_a_new_markdown_block_ends_the_index_table` (15 cases: heading levels/indentation, quotes, list markers, thematic break, HTML/comment, fence styles) | 15 failed before repair; pass |
| Markdown line-ending boundaries | `test_block_boundaries_accept_markdown_line_endings` (LF, CRLF, CR) | 3 failed before repair; pass |
| Real-filesystem CLI accepts a valid index followed by another block | `test_the_script_accepts_an_index_followed_by_another_markdown_block` | exit 1 before repair; now exit 0, empty stderr, success summary |
| Real entries remain visible after another section | `test_a_duplicate_in_another_block_is_still_reported` | passed before repair; exact duplicate diagnostic retained |
| Malformed cells cannot be hidden by Markdown normalization | `test_markdown_cell_normalization_cannot_hide_malformed_rows` (short/extra-cell cases) | passed before repair; exact diagnostics retained |
| Row-shaped examples remain inside their own blocks | `test_rows_inside_other_markdown_blocks_are_not_index_entries` (8 cases) | neighboring cases added on green; pass without further production change |
| Existing valid/rejected input behavior | original 55 ADR tests, including missing/duplicate/unknown rows, metadata, field mismatches, omitted leading pipes, headerless input and CLI failure diagnostics | all retained; pass |

Initial green: **77 passed in 0.14 s**, using the same tests as the expanded red run.
After adding neighboring context tests: **85 passed in 0.14 s**. No tests were deleted,
weakened, skipped or mocked. Numeric ranges are inapplicable to this text parser.

## Gates

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors, warnings, informations |
| Lint | `uv run ruff check .` | pass |
| Formatting | `uv run ruff format --check .` | pass: 180 files already formatted |
| Import boundaries | `uv run lint-imports` | pass: 1 kept, 0 broken |
| Full SQLite suite | `uv run pytest` | pass: 511 tests in 11.25 s |
| Focused ADR tests | `uv run pytest tests/scripts/test_check_adrs.py --tb=short` | pass: 85 tests in 0.14 s |
| Current ADRs | `uv run python -m scripts.check_adrs docs/adr` | pass: 26 ADRs/index consistent |
| Build | `uv build` | pass: source distribution and wheel |
| Lock consistency | `uv lock --check` | pass: 53 packages resolved |
| Diff whitespace | `git diff --check` | pass |

## Observability delivered

No new application events or metrics are appropriate for this local checker, as ticket
21 specifies. The real-filesystem success regression checks exit 0, empty stderr and a
consistency summary. Existing failure regressions retain precise file/field stderr,
exit 1 and no success summary. The repair removes the false discrepancy rather than
suppressing genuine diagnostics.

## Not verified

Code complete is not deployment verified. Independent review of this repair, hosted
GitHub Actions and deployed-commit execution remain pending. Postgres and actionlint
were not rerun for this parser/development-dependency change; earlier results are
historical. The pre-existing compact-empty-final-cell `_parse_row` limitation recorded
in the preceding report is unchanged. The accepted historical AC-59 test-order exception
is unchanged and is not used for this repair.

## Deployment verification checklist

- [ ] On the target commit, run `uv sync --locked` and `uv run python -m scripts.check_adrs docs/adr`: dependency resolution succeeds, exit 0 and all ADRs/index consistent.
- [ ] In a test PR, place a heading, quote, list or fenced example immediately after a valid index without a blank line; pipe-containing text outside the table does not fail the hosted docs check.
- [ ] Add a real duplicate row without a leading pipe: the hosted docs check fails with the duplicate ADR diagnostic and no success summary. Restore the index and confirm it passes.
