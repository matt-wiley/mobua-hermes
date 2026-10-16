# 0009. Secrets use envelope encryption with a deploy-time Master Key

Status: Accepted
Date: 2026-10-16

## Context

Plugins need Source credentials. The system is self-hosted, runs Collections on a schedule while the Reader is logged out, and may later share Plugins publicly.

## Decision

The Core stores Secrets encrypted, per Reader. Each Reader has a data key; Secrets are encrypted with it (AES-256-GCM or similar), and the data key is stored encrypted by the Master Key. The Master Key is supplied at deploy time (env var or Docker secret) and never stored with the data; on first local run the app can generate one and print it for the Reader to save. At the start of a Plugin Run, only that Plugin's Secrets are decrypted, in memory, and passed as environment variables, never logged or written to disk. Rotating the Master Key re-wraps data keys only. The Master Key source is pluggable so larger deployments can use a KMS or Vault.

LLM Provider credentials: added 2026-10-16 (design consistency pass). A Reader's LLM Provider credentials are encrypted with the same Data Key. Unlike Secrets, they are never passed to a Plugin Run: they are decrypted only inside the LLM Gateway, in memory, at call time, and never logged (ADR 0008).

## Alternatives rejected

- **Keys derived from the Reader's login password.** Scheduled Collections run while the Reader is logged out and couldn't decrypt anything.
- **Secrets in Plugin config.** Leaks credentials whenever a Plugin is shared.

## Consequences

- Losing the Master Key makes all stored Secrets unrecoverable; they must be re-entered.
- Anyone with the running container's environment can decrypt Secrets.
