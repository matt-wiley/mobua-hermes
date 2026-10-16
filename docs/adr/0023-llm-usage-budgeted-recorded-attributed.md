# 0023. LLM usage is budgeted, recorded, and attributed

Status: Accepted
Date: 2026-10-16
Amends: ADR 0012

## Context

Every Plugin on a Channel may call any of its Channel Models (ADR 0021), so nothing but a limit prevents runaway LLM cost. A Reader may use several LLM Providers, and when spend or failures cause trouble they need to know which Provider and Model is involved. Provenance (ADRs 0010, 0016) should extend to which Models produced an output, and that record must outlive transient data, as Citations do.

## Decision

**Budgets.** The Gateway enforces daily token budgets, reset at midnight in the Reader's time zone:
- per Channel (default 500k tokens/day), an operational setting on the Channel identity, not on the Channel Revision, since it doesn't shape content;
- per LLM Provider (optional, unlimited by default), a Reader setting;
- per Reader across all Channels and the Core agent (default 2M tokens/day).

A call proceeds only if all applicable budgets have room. Any budget may be set to unlimited explicitly. Budgets count tokens, not money. A refused call is recorded in Channel Health naming the exhausted budget and the call's Provider and Model; unfinished Topics stay unused (ADR 0010).

**Call records.** The Gateway stores one record per call: time, Reader, Channel, caller (Publish step, Plugin Binding, or Core agent), Channel Model name, Provider, Model id, tokens in and out, latency, outcome (ok, error kind, or refusing budget), and whether it was a citation retry. Kept 90 days by default (a Reader setting).

**Metrics.** Prometheus exposes `gateway_calls_total{provider,model,outcome}`, `gateway_tokens_total{provider,model,direction}`, `gateway_call_duration_seconds{provider,model}`, and `gateway_budget_refusals_total{budget,provider}`, with no Reader or Channel labels to keep cardinality bounded.

**Model Health.** A Reader-level record of whether each LLM Provider and Model is reachable and working, fed by call failures, an hourly model-listing check where the Provider offers one (no tokens spent), and a tiny real call when a Provider is saved or tested. A Channel whose Channel Model points at an unhealthy Model links to it from Channel Health.

**Model Attribution.** Every LLM-produced output records which Models were used for which steps (step, Channel Model name, Provider, Model id), copied onto the output so it outlives call records, and linked to them while they exist. Articles attribute every LLM step including citation retries; Style Proposals attribute the Core agent's Model; Plugin Runs attribute their turns, covering the News Items they produce.

## Alternatives rejected

- **Dollar budgets.** Closer to what Readers care about, but needs per-Model prices kept current, and local Models cost nothing. Can be layered on later.
- **Usage reporting without enforcement.** Shows the bill only after it's run up.
- **Prometheus only.** Can't answer per-Article or per-Channel efficiency questions and doesn't survive restarts without a separate Prometheus server.
- **Periodic tiny real calls for Model Health.** Stronger signal, but spends tokens around the clock against the same budgets.
- **Attribution by link to call records only.** Breaks when records expire, leaving Articles unable to say which Model wrote them.

## Consequences

- Budget exhaustion is diagnosable to a specific budget, Provider, and Model.
- Model efficiency can be analyzed from call records joined to Articles and citation outcomes.
- Every LLM-calling code path must go through the Gateway's accounting (already required by ADR 0008) and attach Model Attribution to its output.
- Extends ADR 0012's "cost attribution" from per-Channel token usage to budgets, call records, and attribution.
