# 0008. Channels and Plugins reach LLMs only through the Core's LLM Gateway

Status: Accepted
Date: 2026-10-16
Amended by: ADRs 0020, 0021

## Context

Channels write Articles with LLMs, and Plugins may need LLM turns while organizing what they retrieve. Plugins are subprocesses that may run reader-written or third-party code. A Reader may connect several LLM Providers.

## Decision

The Core holds all LLM Provider credentials and exposes a small internal API, the LLM Gateway. Each Channel uses a set of the Reader's enabled Models as named Channel Models (amended by ADR 0021). During a Plugin Run, the Channel gives the subprocess the Gateway's local endpoint and a short-lived token scoped to that Channel's Channel Models.

## Alternatives rejected

- **Each Channel or Plugin holds its own API keys.** Simple, but spreads secrets into Plugin code and config and hides cost.
- **No LLM access in Plugins.** Simpler and safer, but rules out Plugins that need an LLM to organize what they find.

## Consequences

- Plugins are never given real API keys and cannot read the app's data or the server process's environment (ADR 0020); a leaked token expires quickly.
- LLM cost and usage are attributable per Channel.
- The Gateway is a hard dependency for every Publish and any vetting Plugin.
