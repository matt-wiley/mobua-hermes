# 0012. Build our own thin LLM Gateway over existing provider libraries

Status: Accepted
Date: 2026-10-16
Amended by: ADRs 0021, 0023, 0024

## Context

ADR 0008 puts all LLM access behind the Core's LLM Gateway. LiteLLM (proxy or library) covers most of this already, including virtual keys and spend tracking.

## Decision

Build our own thin Gateway. Its contract is one call: messages in, either text or JSON validated against a schema out, plus token usage for per-Channel cost. No streaming, tool use, or embeddings in v1. Two adapters to start: OpenAI-compatible (OpenAI, Ollama, OpenRouter, LM Studio, vLLM) and Anthropic. Provider calls are delegated to existing libraries underneath; scoped tokens, resolving Channel Model names (ADR 0021), and cost attribution are ours.

Call metadata: amended by ADR 0024. Calls accept extensible tags for local usage analysis,
with automatic Gateway-controlled Test Run markers and forwarding where Providers support it.
Metadata is separate from prompt text.

## Alternatives rejected

- **LiteLLM proxy.** Feature-complete, but a separate service that strains the single-container goal, and far broader than we need.
- **LiteLLM as a library.** Avoids the extra service, but brings a large, fast-moving surface area we'd have to understand to maintain.

## Consequences

- Small contract, easy to maintain and test.
- Each new provider needs an adapter.
- Features beyond the contract (streaming, tool use) must be added deliberately. Adding tool use in particular requires revisiting prompt injection first: today a manipulated model can only produce text.
