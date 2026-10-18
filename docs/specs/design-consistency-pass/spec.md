---
slug: design-consistency-pass
title: Design consistency pass
status: implementing
created: 2026-10-17
updated: 2026-10-17
adrs:
  - docs/adr/0018-plugin-bindings-pin-plugin-revisions.md
  - docs/adr/0019-built-in-plugins-are-shared-and-ejectable.md
  - docs/adr/0020-plugin-runs-hardened-not-sandboxed.md
  - docs/adr/0021-channel-models.md
  - docs/adr/0022-plugin-runtimes-and-pinned-inline-dependencies.md
  - docs/adr/0023-llm-usage-budgeted-recorded-attributed.md
  - docs/adr/0005-plugins-run-as-subprocesses.md
  - docs/adr/0007-all-data-scoped-to-a-reader.md
  - docs/adr/0009-secrets-envelope-encryption.md
  - docs/adr/0010-enforced-citations.md
  - docs/adr/0014-own-db-driven-scheduler.md
  - docs/adr/0024-plugin-drafts-and-permanent-revision-history.md
  - docs/adr/0025-built-in-plugin-identities-and-global-lineage.md
  - docs/adr/0026-interim-two-file-plugin-workspaces.md
external: null
---

# Design consistency pass

## Intent
This is the single in-flight implementation contract. It incorporates the confirmed
[Plugin drafts grill](../plugin-drafts/grill.md) on 2026-10-17; there is no separate
Plugin drafts spec or ticket set. Completed tickets 01–02 and their evidence retain their
original scope. Pending tickets 03–21 are revised and reordered in the
[implementation plan](tickets/README.md), including an old-to-new numbering map.

The design review of 2026-10-16 found contradictions, ambiguities, and gaps across `CONTEXT.md` and the ADRs. The grill resolved all of them, as decisions or as explicit deferrals. The documentation fixes are already in the repo. This spec is the build contract for the **behavior** those decisions introduce or clarify in the service layer and CLI:
- how Channels use Plugins (Plugin Bindings, Built-in Plugins, Eject);
- how Plugin Runs are launched and hardened;
- how Channels and Plugins reach Models (Channel Models, Gateway Tokens);
- how LLM usage is budgeted, recorded, health-checked, and attributed;
- the scheduling, retention, citation, and grouping rules Publish and Collection depend on.
- Reader-owned Plugin Drafts, permanent Revision trees, CLI/API editing, and ephemeral Test Runs.

It is a delta over the existing ADR design, not a full spec of Collection or Publish.

## Decisions
- D-1: This pass decides the contradictions and ambiguities and, for each design gap, either decides it or defers it to a named follow-up. (grill 1)
- D-2: A Plugin is an identity, owned by a Reader or system-owned if it is a Built-in Plugin, with immutable Plugin Revisions. A Plugin Revision holds the Manifest (with config schema) and code, and records its creator. A Channel keeps an identity plus immutable Channel Revisions. A Channel Revision holds Plugin Bindings, each pinned to one exact Plugin Revision and carrying that Channel's config, validated against that Revision's schema. Moving Channels to a new Plugin Revision is explicit, creates new Channel Revisions, and re-validates config. Ownership is on the Plugin and is about scoping; creation is on the Plugin Revision and is provenance only. ([ADR 0018](../../adr/0018-plugin-bindings-pin-plugin-revisions.md)) (grill 2)
- D-3: A Channel Revision may have zero Plugin Bindings. Collections are then skipped and Channel Health flags "no Plugins attached". Publish still runs. (grill 2a)
- D-4: Built-in Plugins are single, system-owned, read-only Plugins with no Reader id. Their Plugin/Revision UUIDs and development lineage are globally assigned and preserved across deployments. Initial bundled installation imports supplied identities and implementations idempotently; it does not generate a local starter or history from content changes. Show only locally available history, without extra ancestor catalogs or placeholders. Readers Eject an independent Reader-owned copy. Future update delivery, patch installation, and rollback are deferred. ([ADR 0019](../../adr/0019-built-in-plugins-are-shared-and-ejectable.md), [ADR 0025](../../adr/0025-built-in-plugin-identities-and-global-lineage.md)) (original grill 3; Plugin drafts grill 13, 21, 31)
- D-5: Plugin Runs are hardened, not sandboxed:
  - a clean environment (basics, declared Secrets, Gateway URL and Gateway Token);
  - a separate unprivileged OS user with no access to the data volume, the Master Key, or the app's files;
  - a temporary directory per run;
  - CPU, memory, and file-size limits.

  Network access is allowed. The trust model is that Readers run only Plugins they trust. ([ADR 0020](../../adr/0020-plugin-runs-hardened-not-sandboxed.md)) (grill 4)
- D-6: The Reader owns LLM Providers and enabled Models. A Channel Revision configures named Channel Models from them, with free-form names that the UI only suggests. Plugins hold no LLM configuration and request turns only by Channel Model name through the Gateway, using a Gateway Token scoped to the Channel's Channel Models. ([ADR 0021](../../adr/0021-channel-models.md)) (grill 5, 5a)
- D-7: Every Plugin bound to a Channel may call any of its Channel Models. A call naming an undefined Channel Model is refused with a clear error and logged to Channel Health. (grill 5b)
- D-8: Collection and Publish remain the Channel's scheduled content processes. Draft Test Run is a manual ephemeral development action, not a new Channel cadence. Checking past Articles is a step of Publish. Vetting is a Channel step, and where it runs is deferred to the Channel contracts grill. (original grill 5c; Plugin drafts grill 23, 32)
- D-9: A Channel's data is logically separate, as rows in the shared database scoped by Channel and Reader. (ADR 0006, grill 6)
- D-10: Channels own their cadences, which live on the Channel Revision, and their next-run-at state. The shared scheduler in the service layer only carries them out. The Core is the central app experience, a design concept; the service layer is the shared code. (ADRs 0002, 0014; grill 7)
- D-11: Inbox semantics and the shape of Aggregation are deferred to the Channel contracts grill. (grill 8)
- D-12: Core–Channel interaction goes only through seven seams: Aggregation, Style reads, LLM Gateway calls, Secret delivery, scheduler run triggers, Channel Health reports, and Channel configuration. (ADR 0006, grill 9)
- D-13: Channel Health records problems needing the Reader's attention: failed Plugin Runs, rejected News Items, refused Channel Model calls, missing Plugin Bindings, budget refusals, and unhealthy Models. Each Plugin Run keeps its own size-capped stderr log, and Channel Health links to the logs of the runs it flags. (grill 10, 26a, 26b)
- D-14: Plugin Run output is all or nothing. It is buffered and ingested only on exit code 0. (ADR 0005, grill 11)
- D-15: An Article with unmatched Citations is regenerated, with the failed Citations given to the writing Channel Model, up to a retry limit on the Channel Revision (default 2). It is then rejected: no Article is published, the failure goes to Channel Health, and the Topic's News Items stay unused. (ADR 0010, grill 12)
- D-16: When both cadences are due, Collection runs before Publish. A run blocked by the Run Lease stays due and is never dropped. (ADR 0014, grill 13)
- D-17: Every ADR carries Status, Date, and two-way Amends/Amended by metadata. (grill 14)
- D-18: Every record carries a Reader id, except Built-in Plugins and their Revisions and app-wide records with no Reader data. Records that belong to a Channel also carry its Channel id. (ADRs 0007, 0013; grill 15)
- D-19: The glossary defines Built-in Plugin, Eject, Plugin Binding, Channel Model, Model Health, Model Attribution, Data Key, and Gateway Token. (grill 16)
- D-20: The ADR index `docs/adr/README.md` is maintained by hand. A CI consistency check is deferred to the first CI setup. (grill 17)
- D-21: ADR 0017 no longer refers to undefined phases. The roadmap is deferred to a roadmap grill. (grill 18)
- D-22: Authentication is deferred to an auth grill, with its required coverage recorded in the grill. (grill 19)
- D-23: LLM Provider credentials are encrypted with the Reader's Data Key and decrypted only inside the Gateway, in memory, at call time. They are never passed to Plugin Runs or logged. (ADR 0009, grill 20)
- D-24: The Core agent uses one Reader-chosen Model and runs on the shared scheduler. Its trigger and proposal flow are deferred to a Style grill. (grill 21)
- D-25: The v1 image ships Python and a POSIX shell. Python Plugins declare their dependencies inline (PEP 723), pinned exactly, and are run with `uv run`. Unpinned dependencies are rejected when a Plugin Revision is validated. ([ADR 0022](../../adr/0022-plugin-runtimes-and-pinned-inline-dependencies.md)) (grill 22)
- D-26: Retrieved content is untrusted data, placed in delimited prompt blocks. The Gateway has no tool use. Article text is rendered through an allowlist sanitizer. Content-level defenses are deferred to the Channel contracts grill. (grill 23)
- D-27: A cadence is either an interval or a cron expression. Cron uses the Reader's time zone (a Reader setting, default UTC). next-run-at is stored in UTC. (grill 24)
- D-28: The Retention Window is set per Channel Revision, default 14 days, and must be longer than the Publishing interval. (grill 25)
- D-29: The Gateway enforces daily token budgets: per Channel (default 500k), optional per Provider (unlimited by default), and per Reader (default 2M). A call proceeds only if all three have room. Any budget may be set to unlimited. Budgets reset at midnight in the Reader's time zone. A refusal names the exhausted budget and the Provider and Model. ([ADR 0023](../../adr/0023-llm-usage-budgeted-recorded-attributed.md)) (grill 26, 26a)
- D-30: Model Health tracks each LLM Provider and Model. It is fed by call failures, an hourly model-listing check that spends no tokens, and a tiny real call on Provider save or test. It is linked from the Channel Health of affected Channels. (ADR 0023, grill 26b)
- D-31: The Gateway keeps one database record per call, for 90 days by default, and exposes four Prometheus metrics with no Reader or Channel labels. (ADR 0023, grill 26c)
- D-32: Every LLM-produced output carries a copied Model Attribution, linked to its call records while they exist. (ADR 0023, grill 26d)
- D-33: The Channel budget is an operational setting on the Channel identity, not the Channel Revision. Settings that shape content stay on the Channel Revision. (ADR 0023, grill 26e)
- D-34: Topics are grouped by an LLM, returning schema-validated JSON, with Channel-enforced output rules. Each LLM step of Publish (grouping, the past-Article check, writing) names a Channel Model. Writing is required, and the other steps inherit it unless set. Judgment steps are typed decisions. ([ADR 0021](../../adr/0021-channel-models.md)) (grill 27)

### Plugin drafts amendment

The following decisions trace every branch of the confirmed [Plugin drafts grill](../plugin-drafts/grill.md).
[ADR 0024](../../adr/0024-plugin-drafts-and-permanent-revision-history.md) governs Reader-owned Drafts and tests;
[ADR 0025](../../adr/0025-built-in-plugin-identities-and-global-lineage.md) governs Built-in identity and lineage.
These decisions qualify D-7/D-13/D-29/D-32 for ephemeral tests: test errors never create
Channel Health or durable test-attribution/output artifacts, while real calls still update
Model Health and normal Gateway usage accounting.

- D-35: Drafts are separate mutable working copies, not Revisions with a draft status or browser-only editor state. Bindings reference immutable Revisions only. (Plugin drafts grill 1)
- D-36: Use Plugin Draft and Promote; Publish retains its Article-writing meaning. (branch 2)
- D-37: A Reader-owned Plugin can have many Drafts, each based on exactly one parent Revision of that Plugin. (branch 3)
- D-38: Drafts apply only to Plugins; Channel editing continues to create Channel Revisions directly. (branch 4)
- D-39: Shared services expose the complete workflow through CLI and API; Web App screens follow when the frontend exists. (branch 5)
- D-40: Test Run is the manual validation/execution workflow defined by D-56 through D-62 and D-66 through D-67; it is ephemeral and never ingests output. (branch 6)
- D-41: Eject creates a Reader-owned starter Revision 1 and copied implementation Revision 2, makes Revision 2 current, and keeps no Built-in lineage link. Existing Bindings are not moved. (branch 7)
- D-42: Amend this existing spec and its pending tickets to incorporate Drafts, Eject, global Built-in identity, metadata, and test exceptions; preserve completed work. (branch 8; subsequent consolidation instruction)
- D-43: ADRs 0024/0025 and reciprocal amendments/index entries record these decisions. (branch 9)
- D-44: Log Draft promotions, explicit deletions, rejected promotions, and version conflicts with ids and safe reason codes; retain no test output/stderr/history and add no new metric families. (branch 10)
- D-45: A newly created Reader-owned Plugin starts with a valid starter Revision 1 that emits no News Items and exits successfully. Built-ins use global development lineage instead. (branch 11)
- D-46: Promotion creates a current Revision and leaves sibling Drafts and all Channel Bindings unchanged. (branch 12)
- D-47: Built-ins remain system-owned/read-only; Readers cannot create Drafts or change the shared current pointer. Readers may bind accessible Revisions or Eject. (branch 13)
- D-48: Promotion atomically validates/copies a Draft into a new Revision, changes the current pointer, and deletes that Draft. Failure changes none of those records. (branch 14)
- D-49: A Draft from an older Revision can be promoted after explicit confirmation that its new Revision replaces the current selection. Copy as-is; do not merge. (branch 15)
- D-50: Reader Revision history is a tree rooted at the starter for new Plugins. Record each promoted Revision's Draft parent. Any existing Revision can become current without creating a Revision or moving Bindings. (branch 16)
- D-51: Revisions and their full Manifest/code/metadata are permanent; do not archive or delete them. Built-ins need not install historical implementations that were never shipped to the deployment. (branch 17)
- D-52: There is no Revision archive/unarchive lifecycle. (branch 18)
- D-53: Promoted Drafts are deleted because their Revision preserves the implementation; permanence applies to Revisions. (branch 19)
- D-54: Readers may permanently delete their unpromoted Drafts. (branch 20)
- D-55: Built-in UUIDs and lineage span app development rather than deployment-local Reader workflows. Initial bundled installation preserves these values; future update mechanisms are deferred. (branch 21)
- D-56: Save accepts unfinished/invalid Manifest/code, including unpinned dependencies. Promote and Test Run validate before proceeding and return field errors on rejection. (branch 22)
- D-57: Test Runs use normal process hardening/limits and real network/LLM calls, but only preview output, validation errors, and stderr. (branch 23)
- D-58: Tests require a selected Reader-owned Channel and temporary config validated against the Draft schema. No Binding is required or created; use that Channel Revision's named Models/budgets and only declared Secrets of the same Reader. (branch 24)
- D-59: Do not persist Test Run history, code/config snapshots, output, stderr, or durable test Model Attribution. Capture execution inputs once in memory from the saved Draft; the Draft remains the saved source. Successful testing is a Reader go/no-go aid, not a persisted promotion gate. (branch 25)
- D-60: Real test LLM calls use normal Channel/Provider/Reader budgets, call records, retention, and metrics. (branch 26)
- D-61: Gateway calls accept per-call metadata and caller tags. The Gateway supplies/protects test_run and Plugin/Draft identifiers for test calls, records metadata locally, and forwards compatible metadata separately from prompts where Providers support it. Unsupported forwarding does not prevent local tagging. Never add arbitrary metric labels. (branch 27)
- D-62: Tests never drive Channel Health, including on unknown Model names or budget refusal. Actual Provider failures still update Model Health; call outcomes and tags remain in usage records. Normal promoted Plugin execution and other Channel Health causes retain their existing behavior. (branch 28)
- D-63: CLI editing is explicit export → edit → save → test → promote. Test/Promote use the saved database Draft; deleting it leaves local exported files alone. (branch 29)
- D-64: Export carries a Draft version marker; Save and Promote check the expected version and reject conflicts without overwriting/promoting unseen changes. (branch 30)
- D-65: Show only locally available Built-in history. Do not ship metadata-only ancestor catalogs, create placeholder Revisions, fetch missing history, or expose unavailable ancestry. (branch 31)
- D-66: Tests may overlap normal Collection/Publish and use shared budgets without acquiring the Channel Run Lease or changing schedules. (branch 32)
- D-67: Test execution is foreground: cancellation, CLI interruption, or API disconnect stops subprocesses, revokes Gateway access, and cleans temporary files. No resumable background job; incurred token usage remains recorded. (branch 33)
- D-68: Preserve existing Reader Plugin Revision ids, numbering, contents, current selections, and Bindings on migration. Apply starter initialization only to new Reader-owned Plugins, without inventing historical parents. (branch 34)
- D-69: Deliver Draft workspace/promotion/history before the process runner; deliver full Test Runs after the real runner, limits, Gateway, call-driven Model Health, accounting, and budgets. Pull exact-pin validation into promotion and call-driven Model Health into the Gateway ticket; periodic checks remain with the scheduler. (branch 35; consolidation instruction)

### Interim workspace file amendment

Added 2026-10-17 after the ticket 03 review found that saves read every file in the workspace
folder, so `.DS_Store` and `__pycache__` broke them. It is governed by
[ADR 0026](../../adr/0026-interim-two-file-plugin-workspaces.md) and qualifies D-63 until a
Plugin design session decides the Plugin file model.

- D-70: A CLI workspace holds exactly `implementation/manifest.toml` and `implementation/main.py`. Save reads only those two regular files and ignores everything else in the folder; deleting `main.py` saves an empty code set. Export refuses a Draft whose saved code has other files rather than dropping them. Storage, services, and the API keep the code-path map unchanged. ([ADR 0026](../../adr/0026-interim-two-file-plugin-workspaces.md)) (user decision, 2026-10-17)

## Scope and non-goals
**In scope:**
- Service-layer behavior and data model for D-2 through D-7, D-13 through D-16, D-18, D-23, and D-25 through D-34, with CLI commands for the operations a Reader performs: binding, upgrading Bindings, ejecting, and setting budgets, caps, the time zone, and Provider tests.
- The Plugin Run launcher hardening (D-5).
- Reader-owned Plugin Draft lifecycle, permanent Revision history, stale-version protection, CLI file editing, API surfaces, and ephemeral foreground Test Runs (D-35 through D-70).
- Gateway accounting: budgets, call records, metrics, Model Health, and Model Attribution.
- Validation rules on save: Binding config, Channel Models, cadences, Retention Window, and pinned dependencies.
- A docs consistency check runnable locally (AC-56). D-17, D-19, D-20, and D-21 are already done.
- Whole-system checks, added in ticket review on 2026-10-17: an end-to-end smoke test (AC-57), repository tests against Postgres (AC-58), and a CI workflow running the core gates and the docs check (AC-59).

**Non-goals:**
- Anything deferred to a named follow-up:
  - Built-in update lifecycle: release/patch delivery, application, rollback, and remote history; initial bundled installation with supplied global UUIDs is in scope.
  - Channel contracts grill: where vetting runs, Inbox and Aggregation, content-level injection defenses;
  - auth grill;
  - Style grill: the Core agent's trigger and proposal flow, and so Style Proposal attribution in practice;
  - roadmap grill: phases and a Model-comparison UI;
  - the discriminative-model spike.
- Web App screens for any of this; they come when the Web App is specified. Draft lifecycle/history/Test Run operations have CLI and API surfaces backed by shared services; existing other tickets retain their stated surfaces.
- Channel Drafts, automatic Revision merges, Revision archival/deletion, persistent test snapshots/history, and resumable background tests.
- Namespace sandboxing of Plugin Runs (ADR 0020).
- Per-Binding Model access control (ADR 0021).
- Dollar-denominated budgets (ADR 0023).
- Embedding-based Topic grouping, which needs embeddings in the Gateway.
- Runtimes other than Python and shell for Plugins (ADR 0022).
- CI for the web module, and running the container-image integration tests in CI. AC-59 covers the core gates and the docs check only.
- Writing the RSS Built-in Plugin or the Publish writing prompt beyond what these criteria require.

## Acceptance criteria

### Plugins, Revisions, and Bindings
- AC-1: Given a Plugin Revision whose config schema requires `url`, when a Channel Revision is saved with a Binding to it whose config lacks `url`, then the save is rejected with a field-level error and no Channel Revision is created.
- AC-2: Given a Channel pinned to an existing Plugin Revision, saving/editing a Draft, promoting another Revision, or selecting a different Plugin current Revision leaves its Binding unchanged. A subsequent Collection runs the originally pinned Manifest and code until an explicit Binding upgrade.
- AC-3: Given three Channels bound to Plugin Revision 1 and a Revision 2 whose schema rejects one Channel's config, when the Reader moves all three to Revision 2, then two Channels get a new Channel Revision bound to Revision 2. The third keeps its current Channel Revision, and the operation reports it with the validation error.
- AC-4: Given Reader A's Plugin, when Reader B saves a Channel Revision binding to any of its Revisions, then the save is rejected. When Reader B binds to a Built-in Plugin Revision, the save succeeds.
- AC-5: Given a Plugin Revision created by a Reader, its creator is that Reader's id. Given one created by seeding, its creator is `system`.
- AC-6: Given a Channel whose current Revision has zero Bindings, when its Collection cadence comes due, then no Collection starts and Channel Health contains a "no Plugins attached" entry. When its Publishing cadence comes due, a Publish runs.

### Built-in Plugins and Eject
- AC-7: On fresh initial installation, import each bundled Built-in Plugin/Revision with its globally supplied UUIDs and development lineage, system provenance, and shipped implementation. Installing the identical bundle again creates no duplicate Revisions or local starter/Draft ancestry. History lists only locally installed Revisions; an absent ancestor does not require a placeholder row or extra history catalog. Do not infer or implement later-release update/rollback behavior in this criterion.
- AC-8: A Reader cannot edit a Built-in, create a Draft on it, add a Revision, or change its shared current pointer. Rejection leaves Built-in state unchanged; listing/binding accessible Revisions and Eject remain allowed.
- AC-9: Eject creates a Reader-owned Plugin with starter Revision 1 and current Revision 2 copied exactly from the Built-in's current Manifest/code, created by that Reader. Revision 2's parent is the new Plugin's starter, with no link to the Built-in. It is immediately bindable without manual Draft promotion; existing Bindings and subsequent independent Built-in changes do not alter the copy.
- AC-10: Built-in Plugin and Plugin Revision rows have no Reader id, and both Reader A and Reader B can list and bind to them through the service layer.

### Plugin Run hardening and output
- AC-11: Given a test Plugin that prints its environment, when it runs with one declared Secret while the server process has the Master Key and an unrelated variable in its environment, then the printed environment contains only the allowlisted basics, the declared Secret, the Gateway URL, and the Gateway Token.
- AC-12: Given a test Plugin that reports its uid and tries to read the database file and the Master Key file, when it runs, then its uid is the Plugin OS user's and both reads fail with permission denied.
- AC-13: Given a test Plugin that exceeds the configured memory, CPU-time, or file-size limit, when it runs, then it is terminated and recorded as a failed Plugin Run in Channel Health with the limit that was hit.
- AC-14: Given two concurrent Plugin Runs, each has its own temporary directory, and neither can read the other's.
- AC-15: Given a test Plugin that writes 5 valid News Items, when it exits 0, then 5 are ingested. When it exits 1 or is killed for timeout after writing them, then 0 are ingested and the run is a failure.
- AC-16: Given a Plugin Run that writes more stderr than the configured cap, its stored log is truncated at the cap and marked truncated. A failed run's Channel Health entry links to that log.

### Channel Models and the Gateway
- AC-17: When a Channel Revision is saved without a writing-step Channel Model, the save is rejected.
- AC-18: Given a Channel Revision that sets only the writing step's Channel Model, when Publish runs, then the grouping, past-Article check, and writing calls all use that Model. When the grouping step names a different Channel Model, grouping calls use it.
- AC-19: When a Channel Revision maps a Channel Model name to a Model that is not among the Reader's enabled Models, the save is rejected.
- AC-20: Given Channel Models `writer` and `vetter`, any Plugin Run of that Channel calling `model("vetter")` reaches the Model mapped to `vetter`.
- AC-21: When a Plugin Run calls an undefined Channel Model name, the Gateway returns an error naming it, makes no provider call, and adds a Channel Health entry.
- AC-22: A Gateway Token issued for a Plugin Run of Channel A is refused when used for Channel B's Channel Models, and refused after it expires.
- AC-23: After saving an LLM Provider with an API key, the stored credential is not the plaintext key, and decrypts only with the Reader's Data Key. A Plugin Run's environment and the server's logs never contain the plaintext key (checked with a known sentinel key).

### Budgets, call records, metrics
- AC-24: Given a Channel budget of 1,000 tokens with 990 already used today, when a call is made, then it is refused before reaching the provider. The Channel Health entry names the Channel budget, the Provider, and the Model.
- AC-25: Given room in the Channel and Reader budgets but an exhausted Provider cap, a call to that Provider is refused naming the Provider budget, while a call to a different Provider proceeds.
- AC-26: Given an exhausted daily budget for a Reader whose time zone is `America/Chicago`, calls are refused until 00:00 America/Chicago and succeed after it.
- AC-27: Given any budget set to unlimited, it never causes a refusal.
- AC-28: When a Reader changes a Channel's budget, no new Channel Revision is created and the new limit applies to the next call.
- AC-29: A new Channel's budget defaults to 500,000 tokens per day, a new Reader's cap to 2,000,000, and a new Provider has no cap.
- AC-30: Given a Publish with three Topics where the budget is exhausted after the first Article, then one Article is published and the other two Topics' News Items remain unused.
- AC-31: Every Gateway call (succeeded, failed, or refused) creates exactly one call record with: time, Reader, Channel, caller, Channel Model name, Provider, Model id, tokens in and out, latency, outcome, citation-retry flag, and extensible call metadata. An ephemeral test caller requires no durable Plugin Run/Binding/Draft foreign-key target; deleting its Draft does not delete usage records or tags.
- AC-32: Call records older than the Reader's retention setting (default 90 days) are removed by a scheduled purge, and newer ones remain.
- AC-33: `GET /metrics` exposes `gateway_calls_total{provider,model,outcome}`, `gateway_tokens_total{provider,model,direction}`, `gateway_call_duration_seconds{provider,model}`, and `gateway_budget_refusals_total{budget,provider}`. None has a Reader or Channel label.

### Model Health
- AC-34: When a Gateway call fails with an authentication, not-found, rate-limit, or timeout error, the Model Health entry for that Provider and Model records the failure kind and time.
- AC-35: The hourly check calls the Provider's model-listing endpoint, records zero tokens, and marks a Model unhealthy when it is missing from the listing.
- AC-36: Saving an LLM Provider, or running its test action, makes one real call per enabled Model with an output limit of 1 token and records the result in Model Health.
- AC-37: Given a Channel whose Channel Model maps to an unhealthy Model, that Channel's Health contains an entry linking to the Model Health entry.

### Model Attribution
- AC-38: A published Article lists one Model Attribution entry per LLM step it used (grouping, past-Article check, writing, and each citation retry), each with step, Channel Model name, Provider, and Model id. The list is still present after its call records are purged.
- AC-39: A Plugin Run that made LLM turns carries a Model Attribution entry for each turn.

### Publish rules
- AC-40: Given a writing Model that returns an Article with one unmatched Citation twice and then a valid one, the third attempt is published. The retry prompts included the unmatched Citations.
- AC-41: Given a writing Model that always returns unmatched Citations and a retry limit of 2, after 3 attempts no Article is published, Channel Health lists the unmatched Citations, and the Topic's News Items remain unused.
- AC-42: Given grouping output containing an unknown id, an already-used id, and an empty Topic, the unknown and used ids are discarded and the empty Topic is dropped. Unused items that no Topic lists stay unused.

### Scheduler, cadences, retention
- AC-43: Given a Channel with both cadences overdue, the Publish starts only after the Collection has completed.
- AC-44: Given a Collection holding the Run Lease when the Publishing cadence comes due, the Publish's next-run-at is not advanced, and it starts on the first poll after the lease is released.
- AC-45: Given a Channel that missed 5 Collection slots while stopped, on wake exactly one Collection runs for them.
- AC-46: An interval cadence (`every 2h`) and a cron cadence (`0 7 * * *`) are accepted. Invalid expressions are rejected at save.
- AC-47: Given cron `0 7 * * *` and time zone `America/Chicago`, the computed runs are 07:00 local on the days before and after a DST change, stored as the corresponding UTC instants.
- AC-48: A new Channel Revision defaults to a 14-day Retention Window. A Revision whose window is not longer than its Publishing interval (for cron, the longest gap between scheduled runs) is rejected at save.

### Plugin runtime and dependencies
- AC-49: A Plugin Revision whose inline script metadata lists `feedparser>=6` is rejected at validation; one listing `feedparser==6.0.11` is accepted.
- AC-50: Given a valid pinned Python Plugin, its Plugin Run is launched with `uv run`, resolves its dependencies, and writes the uv cache only under the Plugin OS user's cache directory.

### Prompt safety
- AC-51: The prompt builder places every piece of retrieved content inside delimited data blocks. A News Item whose text contains the block delimiter is escaped, so it cannot close its block early.
- AC-52: Rendering Article text for display removes `<script>`, event-handler attributes, and `javascript:` URLs, and keeps the allowlisted formatting.

### Data scoping
- AC-53: A schema test confirms every table has a Reader id column, except Built-in Plugin tables and declared app-wide tables. Every table for Channel-owned records also has a Channel id column.
- AC-54: Querying Plugins as Reader B through the service layer returns Built-in Plugins and B's own Plugins, never Reader A's.

### Docs consistency
- AC-55: Every ADR file has `Status:` and `Date:` lines. Every `Amends: X` has a matching `Amended by:` on X, and the reverse.
- AC-56: A local check script verifies that `docs/adr/README.md` lists every ADR file exactly once, with matching title, status, and Amended-by values, and exits non-zero otherwise.

### Whole-system checks
- AC-57: An end-to-end smoke test runs in the container image with the real Plugin Run launcher, SQLite, the real Gateway with a fake Provider Adapter, and an injected clock. A Channel bound to the RSS Built-in Plugin, reading a local fixture feed, is advanced through one scheduler tick. A real Plugin Run collects News Items into the Feed, then the Publish writes at least one Article into the Inbox. Each Citation matches a fixture Source Reference, the Model Attribution names the fake Model for each LLM step, and there is one call record per LLM step.
- AC-58: With `NEWS_TEST_DATABASE_URL` set to a Postgres URL, the repository tests and the schema test (AC-53) run against Postgres and pass. With it unset, they run on SQLite.
- AC-59: A GitHub Actions workflow runs on every pull request and on every push to `main`. It runs core typecheck, lint, the full suite on SQLite, the repository tests against a Postgres service container whose version is pinned in the workflow, and the docs check (AC-56). Any failing step fails the run.

### Reader-owned Draft workspace and Revision lifecycle

- AC-60: Creating a new Reader-owned Plugin produces current starter Revision 1, which emits zero News Items and exits 0. Upgrading a pre-Draft database preserves existing Plugin/Revision ids, numbers, contents, current pointers, and Bindings; it adds no artificial starter or inferred parent relationships to existing history.
- AC-61: A Reader can create/list many Drafts from any existing Revision of their own Plugin. Each starts with copied Manifest/code and exactly that same-Plugin parent. Unknown, foreign-Reader, wrong-Plugin, and Built-in targets are rejected without changes.
- AC-62: Saving a Draft with invalid TOML, unfinished code, or unpinned dependencies succeeds and preserves that text without creating a Revision, moving the Plugin current pointer, or changing Bindings. List/read/save API and CLI operations expose the same saved contents and enforce Reader scope.
- AC-63: CLI export writes the Draft Manifest/code and version marker to a local workspace. Explicit save imports the edited Manifest and `main.py`, including removal of `main.py`, and ignores other files in the workspace (D-70), only if the expected Draft version matches, then advances the marker/version. A stale CLI or API save returns a conflict and leaves stored contents unchanged. Test/Promote use saved database contents, not unsaved local files.
- AC-64: A Reader can permanently delete their unpromoted Draft through CLI/API; foreign-Reader attempts fail. Draft deletion leaves all Revisions, Bindings, and local exported files unchanged.
- AC-65: Valid promotion atomically creates a new immutable Reader-created Revision, makes it current, and deletes only the promoted Draft. Invalid Manifest/dependency pins, a stale expected Draft version, or transaction failure leaves Draft contents, Revision counts, current pointer, and Bindings unchanged. Check state before rollback and committed state where applicable.
- AC-66: Promoting two Drafts based on the same parent produces two new Revisions retaining that parent, with distinct monotonically allocated numbers even after a current-pointer rollback. Sibling Drafts remain editable. An older-parent promotion requires explicit confirmation of the expected current selection and copies the Draft as-is without merging; a changed current selection requires reconfirmation.
- AC-67: CLI/API show the Reader-owned Revision tree and select any Revision of that Plugin as current without creating a Revision or moving Bindings. Unknown, foreign-Reader, and wrong-Plugin Revision selections fail without state changes.
- AC-68: Plugin Revision Manifest/code/ancestry/metadata remain immutable and permanent: service/ORM update and delete attempts fail, and no Revision archive/delete command or endpoint exists. Draft rows remain mutable/deletable; migration under AC-60 is the explicit schema-transition boundary.
- AC-69: CLI/API promotion and history/current-selection operations share service rules and expected-version/current-selection checks. Success is reported only after commit; rejected requests return actionable field/conflict errors. Promotion does not require a retained successful Test Run.

### Ephemeral Draft Test Runs and Gateway metadata

- AC-70: Test Run validates saved Draft Manifest, exact dependency pins, temporary config against its schema, Reader ownership, and the selected Channel before starting a subprocess. An invalid/foreign request starts no subprocess or Provider call, creates no Revision/Binding/Health entry, and returns errors to the caller.
- AC-71: A valid Test Run uses the real restricted process runner and normal limits, returning exit status, output, per-item validation errors, and size-capped stderr with truncation indication. Success, nonzero exit, timeout, and rejected News Items all ingest zero items. After completion retain no Test Run row/history, snapshots, output, stderr, or durable test-attribution artifacts.
- AC-72: A Draft can be tested against a same-Reader Channel with no Binding to its Plugin, using temporary config, only declared Secrets, and that selected Channel Revision's named Models. The test does not create/change Bindings, Channel config, schedules, or Run Lease; normal Collection/Publish may proceed concurrently and all actual calls share normal budgets.
- AC-73: Test calls record normal usage/outcomes/retention with Gateway-controlled test_run: true and Plugin/Draft identifiers. Unknown Channel Model and budget refusal return test errors with no Provider call or Channel Health entry. Test-origin Provider errors update Model Health and usage accounting without emitting a test-driven linked Channel Health entry; normal Channel operation may subsequently surface actual Model Health problems.
- AC-74: Cancelling an active Test Run terminates its subprocess tree, revokes its scoped Gateway access, and removes temporary files. A token reused after cancellation/completion is refused; already incurred usage records remain. There is no resumable/retrievable background Test Run.
- AC-75: CLI interruption and API disconnect trigger AC-74 cleanup, including while a Plugin is waiting on a Gateway turn; surface integration tests verify cleanup and no persisted test output/history. Requests still have the normal Manifest timeout as a backstop.
- AC-76: A Test Run captures saved inputs once at start in memory. Editing, promoting, or deleting the Draft afterward does not change the running implementation or relabel its usage; cleanup does not overwrite the later Draft state or recreate a deleted Draft. No historical snapshot is saved.
- AC-77: The Gateway accepts caller metadata/tags separately from messages, but execution-origin fields (including test_run and test Plugin/Draft ids) come from trusted scoped context. Missing, conflicting, or malicious caller tags cannot suppress/spoof the test marker or change authorization. Normal calls are marked according to their trusted origin too.
- AC-78: A metadata-capable Provider Adapter forwards compatible tags as request metadata, never in prompt text. An Adapter without metadata support omits outbound tags while local usage accounting retains them and the call still works. Adapter contract tests assert both outbound payloads and unchanged message contents.
- AC-79: Successful, failed, and refused calls retain extensible metadata with the normal call record, surviving Draft deletion until normal record retention expiry. Arbitrary tags do not become Prometheus labels, and stored metadata contains no injected Secret/Provider/Master Key/Gateway token values.
- AC-80: A Test Run does not trigger regular Plugin Run failure/rejected-item events or create Channel Health, including on timeout or limit exhaustion. It still increments existing Gateway metrics for actual calls and may update Model Health; it adds no new metric families or labels.
- AC-81: Draft promotion/deletion/rejection/conflict operations emit the assigned structured service events with Reader/Plugin/Draft/Revision ids as applicable and safe reason/field codes. Logs contain no Manifest/code/config payloads or credential values. CLI logs use its configured file and API logs use stdout; test stdout/stderr are returned only to the invoking caller.
- AC-82: A container smoke test creates a Reader-owned Draft, saves an implementation that makes a tagged Gateway call, tests it with the real runner and fake Provider edge, verifies preview/usage with no ingestion/history/Health effects, promotes it, binds its Revision explicitly, and collects using the promoted code. Revision ancestry, pinned execution, Model Attribution for the normal run, and absence of leaked credentials all survive the complete flow.

## Design notes
- **Pure core** (no I/O; unit-tested):
  - validating Binding config against a JSON Schema;
  - deciding Binding eligibility (owner or built-in rule, D-4);
  - resolving the Channel Model for a step, with inheritance;
  - parsing cadences and computing next-run times (interval, cron with `zoneinfo`);
  - checking the Retention Window against the Publishing interval;
  - deciding the Catch-up and ordering;
  - deciding budgets: given usage and limits, return allow or refuse with the budget named;
  - checking PEP 723 pins;
  - matching Citations and building retry feedback;
  - validating grouping output;
  - building delimited prompt blocks;
  - building Model Attribution;
  - sanitizing Article HTML;
  - comparing bundled global identities/content for idempotent initial Built-in installation;
  - Draft ownership/parent checks, expected-version conflicts, promotion/current-selection rules;
  - protected execution metadata construction and Provider metadata capability mapping.
- **Edges:**
  - the repositories (SQLAlchemy 2.1 over SQLite/Postgres);
  - the Plugin Run launcher (subprocess, uid switch, clean env, rlimits, temp dir, `uv run`);
  - the Gateway's Provider Adapters and model-listing calls;
  - the scheduler loop and Run Lease;
  - envelope encryption with the Master Key;
  - the Prometheus registry;
  - the clock;
  - the CLI (Typer) and API (FastAPI).
  - Draft file export/import (Manifest and `main.py` only, D-70) and version markers; surface-owned commit/response ordering;
  - ephemeral execution input capture, process-tree cancellation, token revocation, and temporary cleanup.
- **Test seams:**
  - the clock is injected (AC-26, AC-32, AC-43–47);
  - Provider Adapters sit behind an interface with a fake for budget, Model Health, and attribution tests;
  - the repositories run against SQLite in tests;
  - the launcher sits behind an interface for the service-layer tests.
- **Real integration tests:**
  - launcher hardening (AC-11–14, AC-50), in the container image with the Plugin OS user present;
  - `uv run` dependency resolution against a local package index or a pre-seeded cache;
  - one contract test per Provider Adapter for the model-listing call;
  - the end-to-end smoke test (AC-57), the one test that composes the scheduler, the real launcher, Collection, the Gateway, and Publish.
- **Database portability:** repository tests take their database from `NEWS_TEST_DATABASE_URL` and default to SQLite (AC-58).
- **Ancestry and identity:** Reader-owned parents belong to the same Plugin; Built-in global ancestry may reference absent implementations and must not require fake local rows. The storage representations may differ. Allocate new Reader Revision numbers from the complete retained history, not from the currently selected Revision.
- **Migration:** add a new migration, preserving completed migrations and existing Reader data. Preserve unrecorded legacy ancestry as unknown roots rather than inferring relationships from numbers.
- **Ephemeral state:** no durable Test Run/caller row is necessary. Scoped tokens carry trusted test context and call records retain identifiers as historical values after Draft deletion. Capture input once in memory, perform no long-lived database transaction while a subprocess executes, and reconcile no Draft changes at completion.
- **Staging:** exact-pin parsing/validation ships with promotion before process execution. Call-driven Model Health ships with Gateway core; hourly listing checks are attached to the later scheduler. Thus there is no dependency cycle between Draft promotion, runner, budgets, and tests.
- **Defaults introduced by this spec** (not decided in the grill; adjustable settings):
  - stderr log cap: 1 MiB per Plugin Run;
  - Plugin Run limits: 512 MiB memory, 300 s CPU time, 100 MiB per file written;
  - Gateway Token lifetime: the Plugin's Manifest timeout plus 60 s.

## Observability
- **Logs** (structlog JSON to API/server stdout and the configured CLI log file; never Secrets, provider keys, Gateway Tokens, or the Master Key):
  - `warning` `plugin_run.failed`: Channel id, Plugin Revision id, exit code or limit hit, duration, log reference.
  - `warning` `news_item.rejected`: Channel id, Plugin Run id, News Item id, reason (e.g. no Source Reference).
  - `warning` `channel_model.unknown`: Channel id, Plugin Run id, requested name.
  - `warning` `gateway.budget_refused`: Reader id, Channel id, budget (channel, provider, or reader), Provider, Model, used and limit.
  - `warning` `gateway.call_failed`: Provider, Model, error kind, latency.
  - `warning` `model_health.degraded`: Provider, Model, check type, failure kind.
  - `warning` `article.citations_unmatched`: Channel id, Topic id, attempt number, unmatched count.
  - `error` `article.rejected`: Channel id, Topic id, attempts, unmatched Citations.
  - `info` `channel_revision.rejected`: Channel id, validation errors (Binding config, Channel Models, cadence, Retention Window).
  - `info` `collection.skipped_no_bindings`: Channel id.
  - `info` `scheduler.run_deferred_by_lease`: Channel id, cadence, lease holder run id.
  - `info` `builtin_plugin.seeded`: Built-in Plugin UUID, installed global Revision UUID, content hash; initial bundled installation only.
  - `warning` `run_lease.expired`: Channel id, run id, held duration.
  - `info` `plugin_draft.promoted`: Reader id, Plugin id, Draft id, parent/new Revision ids.
  - `info` `plugin_draft.deleted`: Reader id, Plugin id, Draft id; explicit discard only, not duplicate logging of promotion cleanup.
  - `info` `plugin_draft.rejected`: Reader id, Plugin/Draft ids, safe reason and field codes; promotion rejection only, never raw Manifest/code/config.
  - `info` `plugin_draft.conflict`: Reader/Plugin/Draft ids, operation, expected/actual version or current-selection ids, safe reason.
- **Test exception:** regular Plugin Run/News Item/Channel Health logging applies to promoted execution. Do not persist test stdout/stderr or test-specific failure logs. Real Gateway call outcomes, protected metadata, metrics, and Model Health observations remain ordinary accounting; include trusted test origin where relevant without emitting test-driven linked Channel Health.
- **Metrics** (prometheus-client): the four Gateway metrics in AC-33. No other metrics in this spec, because Channel Health, Model Health, and the call records already cover per-Channel and per-Reader detail, and further labels would make the series count grow with the number of Readers.

## Deployment verification checklist
- [ ] `docker run` with a Master Key, then `GET /metrics`: all four `gateway_*` metric families are present, with no `reader` or `channel` labels.
- [ ] CLI: create a Channel with no Plugin Bindings and wait one Collection interval. Channel Health shows "no Plugins attached", and `docker logs` shows `collection.skipped_no_bindings`.
- [ ] CLI: bind the RSS Built-in Plugin and run a Collection. News Items appear in the Feed, and the Plugin Run's process (`docker exec … ps -o user,cmd`) runs as the Plugin OS user via `uv run`.
- [ ] Run the env-dump test Plugin: its log shows no Master Key or provider key variables.
- [ ] CLI: set a Channel budget to 1 token and trigger a Publish. Channel Health names the Channel budget, the Provider, and the Model; `gateway_budget_refusals_total{budget="channel"}` incremented; no new Channel Revision was created by the budget change.
- [ ] CLI: run the Provider test action. Model Health shows each enabled Model as healthy. Break the key and re-test: Model Health shows an auth failure, and Channels using that Provider show a linked Channel Health entry.
- [ ] Publish an Article and inspect it via the CLI. Its Model Attribution lists each LLM step with Provider and Model id.
- [ ] Run the docs consistency check (AC-56) on the deployed commit: exit 0.
- [ ] Open a PR and confirm the core CI workflow runs every step and passes. A branch with a broken ADR index fails the docs-check step.
- [ ] CLI/API: create a new Reader Plugin, export/save an invalid Draft, then try promotion. Saving succeeds; promotion reports field errors with unchanged Draft/Revisions/current pointer. Correct/save/promote it: a new permanent Revision becomes current and only that Draft disappears; inspect the assigned safe events in the CLI log or server stdout.
- [ ] Export a Draft on macOS, open `implementation/` in Finder and run `main.py` once, then edit `main.py` and save. Saving succeeds despite `.DS_Store` and `__pycache__/`, and the saved Draft's code holds only `main.py`. Exporting a Draft saved through the API with an extra code file fails with an actionable error and creates no directory.
- [ ] Export a Draft, update it through the API, then save/promote the stale workspace version: receive a conflict and observe no overwritten content. Reconcile explicitly. View the Revision tree and select an older Revision; existing Channel Bindings remain unchanged.
- [ ] Test a saved Draft using a selected Channel without creating a Binding. Output appears only to the caller; Feed, Channel config/schedule/lease/Health stay unchanged. Inspect usage records for test_run and Plugin/Draft tags and verify real token consumption/refusals and Model Health behavior. No test artifacts remain after completion.
- [ ] Start a test that waits, then interrupt the CLI and disconnect an API client in separate trials. Confirm subprocesses terminate, scoped tokens stop working, temporary directories disappear, and incurred Gateway usage remains.
- [ ] On two fresh installations of the same bundle, inspect Built-in Plugin/Revision UUIDs: they match. Repeating initial installation adds no duplicates; only local history is shown. Reader edit/Draft/current-pointer requests fail. Eject produces an independent starter plus copied current Revision without moving existing Bindings.
- [ ] Upgrade a pre-Draft fixture/deployment with non-sensitive sample Reader data. Existing Revision ids/numbers/contents/current pointers and Bindings remain identical; no synthetic starter or ancestry appears in that existing history.
