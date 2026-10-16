# 0021. Channels configure named Channel Models; Plugins reach LLMs only through them

Status: Accepted
Date: 2026-10-16
Amends: ADRs 0008, 0012

## Context

ADR 0008 said each Channel uses one Model, while also scoping Plugin tokens to "that Channel's Models", and ADR 0012 mentioned per-Channel Model allowlists. A Channel may want several Models for different jobs (writing, vetting, checking its history), and Plugin code should not depend on which provider or Model a Reader happens to use.

## Decision

- **The Reader owns LLM access.** LLM Providers (URLs, credentials) and enabled Models belong to the Reader and are held by the Core (ADR 0008, unchanged).
- **A Channel Revision configures a set of Channel Models.** Each maps a name chosen by the Channel owner (free-form; the UI only suggests names like `writer` or `vetter`) to one of the Reader's enabled Models. Each LLM step of Publish (grouping Topics, checking past Articles, writing) names the Channel Model it uses; a Channel must set the writing step's, and the other steps inherit it unless set, so a simple Channel configures one Model. Citation retries use the writing step's Model. Because they live on the Channel Revision, Model choices are part of an Article's configuration lineage (ADR 0016).
- **Plugins hold no LLM configuration.** A Plugin Run may request turns through its Channel by Channel Model name only, e.g. `channel.model("vetter").send(prompt)`. Underneath, this is a Gateway call with the Run's short-lived token (ADRs 0008, 0015), which is scoped to its Channel's Channel Models.
- **No per-Binding access control.** Every Plugin bound to a Channel may call any of that Channel's Channel Models.
- **Unknown names are refused.** A call naming a Channel Model the Channel doesn't define gets a clear error and is logged to Channel Health.
- **Judgment belongs to the Channel.** Plugins retrieve and organize; vetting and checks against past Articles are Channel steps within the existing processes, not new processes. Checking past Articles is a step of Publish. Whether vetting is a step of Collection or Publish is decided with the Plugin-to-Channel and Channel-to-Core contracts.

## Alternatives rejected

- **One Model per Channel for everything.** Simplest, but forces vetting and writing onto the same Model and cost profile.
- **Per-Binding Model grants (default none).** Least privilege, but more configuration than a Reader running their own trusted Plugins needs (ADR 0020's trust model).
- **Plugins reference provider Model ids directly.** Couples Plugin code to a Reader's providers; swapping a Model would mean editing Plugins.

## Consequences

- Swapping a Model is a Channel config change; Plugin code is untouched.
- Built-in Plugins can document the Channel Model names they use, but must handle a name being absent.
- Judgment steps (grouping, checking past Articles, and vetting wherever it lands) are defined as typed decisions: a state plus typed questions with typed answers. Generative Models answer them through schema-validated JSON; this leaves room for discriminative models later, which would need a new Gateway call type (a deliberate ADR 0012 change).
- Any bound Plugin can spend on any Channel Model, so spend limits are the only guard against runaway LLM cost.
- Amends ADR 0008 (one Model per Channel; Plugins vetting with LLMs) and ADR 0012 (per-Channel Model allowlists).
