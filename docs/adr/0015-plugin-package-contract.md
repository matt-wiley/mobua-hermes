# 0015. Plugins have a TOML manifest and are invoked over stdin/stdout

Status: Accepted
Date: 2026-10-16
Amended by: ADR 0016

## Context

ADR 0005 runs Plugins as language-agnostic subprocesses. They need a consistent way to declare what they need and exchange data with their Channel.

## Decision

A Plugin has a TOML Plugin Manifest declaring: name, command, a JSON Schema for its config, required Secrets, and timeout. At run time the Channel passes config as JSON on stdin, and Secrets plus the LLM Gateway URL and scoped token as environment variables. The Plugin writes News Items as JSON lines to stdout and logs to stderr, which is kept with the Plugin Run (capped in size) and surfaced in Channel Health when the run has problems. Exit code 0 is success; anything else is failure.

Storage: amended by ADR 0016. Plugins are database records, not directories on disk.

## Alternatives rejected

- **Config via command-line args or files.** Awkward for nested config and risks leaking Secrets into process listings.
- **An HTTP callback API for Plugins.** More flexible, but every Plugin would need an HTTP client and the contract gets bigger.

## Consequences

- Any language works with nothing beyond stdin, stdout, and env vars.
- The config schema lets the Web App generate config forms.
- Future: the Web App should include a TOML editor (for records, per ADR 0016).
