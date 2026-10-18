---
id: design-consistency-pass-02
title: Envelope-encrypted Secrets and LLM Provider credentials
status: done
blocked_by: [design-consistency-pass-01]
external: null
---

# Envelope-encrypted Secrets and LLM Provider credentials

## Goal
Implement the Master Key / Data Key envelope scheme (ADR 0009) and store Secrets and LLM Provider credentials encrypted with the Reader's Data Key, with CLI commands to add a Secret and an LLM Provider.

## Criteria covered
AC-23 (storage and logging part; the Plugin Run environment part is verified in ticket 03)

## Seams
- Pure core: encrypt/decrypt with an injected key source; key wrapping.
- Edges: Master Key source (env var / Docker secret), repositories.
- Test with a fixed test Master Key and a sentinel provider key.

## Observability
- None new. Verify no log line ever contains the sentinel key.

## Verification
- AC-23: stored credential differs from plaintext and round-trips only with the right Data Key; wrong Master Key fails to decrypt; logs captured during save and use never contain the sentinel.
- Edge: first-run Master Key generation prints once and is not stored with the data (ADR 0009).

## Out of scope
- Decrypting provider keys inside the Gateway (ticket 09).
- Injecting Secrets into Plugin Runs (ticket 03).
- Master Key rotation tooling; KMS/Vault sources.
