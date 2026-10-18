# Fix report: Starter Manifest TOML escaping

- **Covers:** `2176d50..` the fix commit on branch `feat/design-consistency-pass`.
- **Source:** the major Standards finding in `docs/specs/design-consistency-pass/report.md` (ticket `design-consistency-pass-03`, AC-60 "valid starter").
- **Date:** 2026-10-17.

## Reproduction (criterion)

- **Expected:** `create_plugin` always commits a Revision 1 whose Manifest parses with `parse_manifest`, whatever non-blank name it is given.
- **Actual:** if the name contains U+007F (DEL), the committed starter Manifest is invalid TOML. The failure only surfaces later, wherever the Manifest is parsed.
- **Root cause:** the name was written into the TOML with `json.dumps(name, ensure_ascii=False)`. JSON escaping is not TOML basic-string escaping: JSON leaves DEL raw, and TOML forbids it. Setting `ensure_ascii=True` would not fix it, because JSON would then escape non-BMP characters as surrogate pairs (`😀`), which TOML also rejects.
- **Fix:** `src/news/service/plugins.py` now has a private `_toml_string` encoder. It escapes `\` and `"`, and writes U+0000–U+001F and U+007F as `\uXXXX`. Every other character is kept as-is.

## Evidence

| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| Starter Manifest parses for any non-blank name | `tests/service/test_plugin_starter.py::test_new_plugin_has_a_valid_noop_starter` with new names: `"delete\x7fcharacter"`; C0 controls `\x01\x08\x0b\x0c\x1b\x1f` with a literal backslash and a literal `A`; U+0080 and U+2028 | yes: existing names | n/a: blank names are still rejected by `test_blank_name_rejected_without_rows_or_payload_logs` | yes: U+001F/U+007F at the edges of the escaped range, and U+0080 just past it | yes: backslash before `u`, quotes, emoji, newline, Unicode line separator | yes | yes |

**Red** (the new test before the fix):

```
FAILED tests/service/test_plugin_starter.py::test_new_plugin_has_a_valid_noop_starter[delete\x7fcharacter]
news.service.manifest.PluginRevisionRejected: (root): invalid TOML: Illegal character '\x7f' (at line 1, column 15)
1 failed, 6 passed
```

The other new cases passed before the fix. They cover the neighbouring boundaries, which JSON escaping already handled correctly.

**Green:** 7 passed in that file after the fix.

## Gates

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass: 0 errors |
| Lint | `uv run ruff check . && uv run ruff format --check . && uv run lint-imports` | pass: 153 files formatted, 1 contract kept |
| Full suite | `uv run pytest` | pass: 293 tests |

## Observability added

None. The bug was a silent bad write, and it is now removed at the cause: every generated starter is valid, so there is no new failure mode to log. Invalid Manifests that Readers write themselves are still rejected and logged by the existing parse and validation path.

## Not verified

- Deployment, and PostgreSQL storage of names containing control characters. PostgreSQL rejects NUL (U+0000) in `text` columns for `plugin.name`; that is a separate, pre-existing issue at the storage layer and was deliberately not tested here.
- The second major from the review (the inverted FastAPI `scope` rule in `docs/standards.md:55`) and the minors. They are outside this fix.

## Deployment verification checklist

- [ ] On the deployed build, create a Plugin through the CLI or API with a name containing DEL, for example `printf 'probe\177name'`. Read its Revision 1 Manifest back and parse it (`python -c 'import tomllib,sys; tomllib.loads(sys.stdin.read())'`). It parses, and `name` round-trips exactly.
- [ ] Inspect server stdout and the CLI log for that create. There is no `plugin.rejected` entry, and no Manifest parse error in later operations on that Plugin.
