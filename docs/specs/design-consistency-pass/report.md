# Code-complete report: Design consistency pass (ticket 02)

- **Covers:** `0d34a6ea83c44bdb80086cd15afa2e7b13132f82..6116d5ef8b568d0eff0ab159ff1a60a183026de9` on `feat/design-consistency-pass--codex-test`.
- **Branch merge-base:** `b1afb214eb1e3b059373079ad2fa2a2c5f4f55d9` with `origin/main`. The requested review focuses on ticket 02's delta above; earlier branch work is context, not independently re-reviewed.
- **Spec:** `docs/specs/design-consistency-pass/spec.md`.
- **Tickets:** `design-consistency-pass-02`, status `done`. AC-23 storage/logging and ADR 0009 setup are in scope. Plugin environment isolation belongs to ticket 03; Gateway credential use belongs to ticket 09. This is not completion of the whole spec.
- **Sync:** n/a; ticket has `external: null`.
- **Date:** 2026-10-17.

## Verdict

**CODE COMPLETE** for ticket 02: Standards, Spec, and Code-complete evidence reviews pass. One nonblocking standards minor remains in test code. All configured core gates pass, including 186 tests.

Three parallel fresh-context reviewers independently inspected the fixed commit without editing files. The evidence reviewer ran all configured gates; the Spec reviewer also ran the 39 focused cases. The coordinating reviewer inspected the delta, code, tests, and ADR 0009 and consolidated results. This report replaces the earlier ticket-01 report, which remains in Git history.

## Findings

No blockers or majors.

### Standards

- **[minor] `tests/service/test_credentials.py:23`** — Source: `docs/standards.md`, SQLAlchemy standards: "Never build SQL with f-strings." The table-existence test uses `text(f"SELECT count(*) FROM {name}")`. Its fixed table-name list prevents injection, so this is nonblocking. Fix: use `select(func.count()).select_from(Base.metadata.tables[name])`.
- **Verdict:** pass. No functional or security defect found. Encryption is pure; randomness and persistence remain at the storage edge. Authenticated context binds ciphertext to Reader/type/record identity. Failure messages and logs exclude supplied credential material.
- **Snapshot:** matches installed and locked dependencies: Python 3.14.6, FastAPI 0.143.3, SQLAlchemy 2.1.5, Alembic 1.20.0, Typer 0.27.3, Pydantic 2.14.1, cryptography 50.0.2. No major-version mismatch.

### Spec

- None. **Verdict:** pass for ticket 02's portion of AC-23 and ADR 0009.
- Tests assert committed Provider ciphertext differs from plaintext, decrypts with its owner's Data Key, and rejects another Reader's key. Secrets and Provider credentials share one wrapped Data Key per Reader. Wrong Master Keys and swapped ciphertext fail authentication.
- Explicit `news key generate` satisfies ADR 0009's optional first-local-run generation. It prints one key line per invocation without retaining it. Configured or previously used keys prevent generation; repeated explicit generation before configuration or encrypted data exists is documented.
- Hidden CLI prompts and committed saves implement the requested Secret and Provider commands. No unrelated scope expansion or ADR contradiction found.

### Code-complete evidence

- None. **Verdict:** pass. `evidence/02.md` records red failures for missing behavior followed by green runs. History confirms tests were committed with production changes in `544e1d9`, `305f3e6`, and `de7a685`. Later assertions extend the initial isolation/authentication coverage.
- Happy paths, failure modes, boundaries, and edge cases are covered narratively and in actual tests. No tests were deleted, weakened, skipped, or marked xfail in the ticket delta.
- Introduced boundaries use real cryptography, migrated SQLite, real key files, CLI calls, and committed reads. No internal collaborators are mocked. No Provider network boundary is introduced.

## Criteria evidence

Test names below are from `tests/service/test_credentials.py`, `test_encryption.py`, `test_keys.py`, and `tests/cli/test_credentials.py`. There are 39 new test cases.

| Criterion | Tests (names) | Happy | Failure | Boundary | Edge | Red-first | Green |
|---|---|---|---|---|---|---|---|
| AC-23: encrypted storage and per-Reader envelope | `test_provider_and_secret_use_one_wrapped_reader_key`; `test_provider_updates_and_identical_names_remain_reader_scoped`; `test_readers_cannot_read_each_others_secrets_or_use_each_others_keys`; `test_secret_updates_reuse_key_and_keep_only_ciphertext`; `test_credentials_have_reader_scoped_tables` | yes: committed round-trip, shared wrapped key | yes: wrong Reader's key rejected | yes: empty/Unicode via encryption tests | yes: updates, identical names across Readers | yes: slices 1–2, `544e1d9`, `305f3e6` | yes |
| AC-23 / ticket: authentication and safe logging | `test_wrong_master_key_fails_without_replacing_the_reader_key`; `test_ciphertexts_cannot_be_swapped_between_secret_records`; `test_wrapped_data_keys_cannot_be_swapped_between_readers`; `test_decryption_rejects_wrong_keys_context_and_damaged_data`; `test_cli_saves_credentials_without_echoing_or_logging_them`; `test_saving_with_a_missing_or_wrong_key_leaves_credentials_unchanged` | yes: save/unwrap/use without sentinel in logs | yes: wrong keys, tampering, safe failure events | yes: truncated ciphertext, key/nonce lengths | yes: swaps, unchanged stored credentials | yes: slices 1–3, `544e1d9`, `305f3e6`, `de7a685` | yes |
| ADR 0009 / ticket: Master Key sources and generation | `test_master_key_can_come_from_environment`; `test_docker_secret_file_is_read_without_changing_it`; `test_invalid_missing_and_conflicting_sources_fail_without_logging_key_values`; `test_non_ascii_key_files_are_reported_safely`; `test_first_run_generation_prints_one_key_and_stores_nothing`; `test_generation_refuses_to_replace_a_lost_key` | yes: env/file, one generated key line | yes: missing/malformed/conflicting/unreadable sources | yes: empty, wrong-length, non-ASCII | yes: configured/used key refused, file unchanged | yes: slice 3, `de7a685` | yes |

All four categories apply to the combined in-scope behavior and are exercised; none is silently omitted. Plugin environment and Gateway-use assertions are deferred portions, not claimed coverage here. CLI tests verify stored database bytes exclude the sentinel, generated keys are absent from logs and environment, and failed saves preserve existing credentials.

## Gates

Fresh runs at `6116d5ef8b568d0eff0ab159ff1a60a183026de9`:

| Gate | Command | Result |
|---|---|---|
| Typecheck | `uv run pyright` | pass; 0 errors, 0 warnings, 0 informations |
| Lint | `uv run ruff check .` | pass |
| Format | `uv run ruff format --check .` | pass; 135 files already formatted |
| Imports | `uv run lint-imports` | pass; 1 contract kept, 0 broken |
| Full suite | `uv run pytest` | pass; 186 tests, 0 skipped, 4.76 s |
| Focused spec verification | `uv run pytest tests/service/test_encryption.py tests/service/test_credentials.py tests/service/test_keys.py tests/cli/test_credentials.py -q` | pass; 39 cases |
| Diff whitespace | `git diff --check 0d34a6e 6116d5e` | pass |

The full suite includes migration/schema drift checks and installed-wheel migration packaging coverage. No production code changed during review; only this report was written afterward.

## Observability delivered

- **Logs:** `warning keys.source_failed` with fixed reasons; `warning credentials.decrypt_failed` with Reader id; `info credentials.secret_not_found` with Reader and Secret ids. CLI logs go to its configured JSON log file; server logging is configured for stdout. Service capture and actual CLI log/output tests exclude the sentinel on success and failure. Generated Master Keys are excluded from logs.
- **Metrics:** none new, as justified in `evidence/02.md`. The spec reserves metrics for four Gateway families, implemented in later tickets.

## Not verified

Code complete is not deployment verified. This review did **not** verify:

- Deployment, container runtime behavior, server stdout under real traffic, or production data.
- Postgres execution; these tests run on SQLite. Postgres testing is ticket 21.
- Plugin Secret delivery and environment isolation (ticket 03), or Provider decryption and calls through the Gateway (ticket 09).
- Master Key rotation tooling or KMS/Vault implementations, explicitly outside this ticket.

## Deployment verification checklist

- [ ] **Initial setup:** apply `news db upgrade`, then run `news key generate` with no key source configured on a fresh database. Confirm one key line is printed. Save it outside the database; supply it through exactly one of `NEWS_MASTER_KEY` or `NEWS_MASTER_KEY_FILE` afterward.
- [ ] **Persist and restart:** create a Reader, then use `news secret set --reader <id> FEED_TOKEN` and `news provider add --reader <id> --url <provider-url> Local` with disposable credentials. Restart with the same Master Key; confirm the service can read the Secret. Inspect `reader_data_key`, `secret`, and `llm_provider`: key/credential fields contain ciphertext and no plaintext test credential.
- [ ] **Wrong-key protection:** supply a different valid Master Key and attempt credential update/use. Confirm failure, then restore the original key and verify the original credential remains usable and unchanged.
- [ ] **Key file:** repeat a credential operation using mounted `NEWS_MASTER_KEY_FILE`, with `NEWS_MASTER_KEY` unset. Confirm success and that the file is unchanged.
- [ ] **Log inspection:** inspect CLI JSON logs and deployed server stdout for the test credential and Master Key values; neither appears. Wrong-key failure records `credentials.decrypt_failed` with Reader id and no supplied key material.
