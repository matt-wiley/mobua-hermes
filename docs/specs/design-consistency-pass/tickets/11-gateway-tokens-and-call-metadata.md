---
id: design-consistency-pass-11
title: "Scoped Gateway tokens, Plugin turns, and protected call metadata"
status: todo
blocked_by: [design-consistency-pass-05, design-consistency-pass-10]
external: null
---

# Scoped Gateway tokens, Plugin turns, and protected call metadata

## Goal
Issue scoped Gateway access for normal Plugin Runs and ephemeral test contexts, expose Plugin turns by Channel Model name, and add protected per-call metadata with Provider capability-aware forwarding.

## Criteria covered
AC-20, AC-21, AC-22, AC-39, AC-77, AC-78

## Seams
- Pure core: token claims/expiry/revocation/origin, Channel Model name resolution, trusted metadata construction, normal Plugin Run attribution.
- Edges: HTTP endpoint, Python helper, runner env delivery, Provider Adapter metadata translation.
- Trusted test context carries Reader/Channel/Plugin/Draft ids without creating a persistent test Run/Binding. A common revocation seam supports completion and later cancellation.
- Caller tags cannot override execution origin, authorization, or reserved test/identity fields. Keep tags separate from prompt messages.

## Observability
- Normal unknown names emit warning channel_model.unknown and Channel Health. Test unknown names return only the error and accounting outcome; test output is not logged.
- Use gateway.call_failed safely for real Provider failures. No arbitrary metadata Prometheus labels.

## Verification
- AC-20/21: any bound Plugin can reach a configured named Model; unknown names cause zero Provider calls and normal Health, with no Health for trusted test context.
- AC-22: cross-Channel, expired, and revoked tokens are refused; lifetime defaults to Manifest timeout plus 60 seconds, with explicit end-of-execution revocation.
- AC-39: normal Plugin Runs copy Model Attribution per turn. Ephemeral test attribution is not persisted as an artifact.
- AC-77: caller metadata cannot spoof/suppress test_run or protected identifiers or change grants; normal/test markers derive from trusted context.
- AC-78: supporting adapters receive compatible outbound metadata; unsupported adapters omit it while the call succeeds with unchanged messages and retained local call metadata input. Durable storage is 12.

## Deployment verification
- Supply scoped access/forwarding assertions for normal Collection and ephemeral test checks. Revocation is exercised end to end by 16.

## Out of scope
- No persistent Test Run record/Binding, token authorization based on caller tags, per-Binding Model ACL, or test UI. Usage storage is 12.
