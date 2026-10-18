# Design consistency pass: revised implementation plan

This is the existing 21-ticket stream, amended after the confirmed
[Plugin drafts interview](../../plugin-drafts/grill.md). The contract is the existing
[spec](../spec.md); no separate Plugin drafts spec or ticket set is required.

Tickets 01–02 are complete and unchanged. Tickets 03–21 were rewritten and
renumbered on 2026-10-17. Completed reports and evidence still use the original pending
numbers; use the historical map below when reading them. This plan does not claim the
amended spec is code complete.

Ticket 03 is implemented; its [evidence](../evidence/03.md) records the starter, migration,
saved Draft services, workspaces, and CLI/API gates. Independent review remains separate.

## PR groups

Each group ships as its own branch and pull request. Do not start a group's tickets on
an earlier group's branch. Branch the next group from the previous group's branch while
that PR is still open (a stacked PR), or from `main` once it has merged. Tickets within a
group still follow the ticket workflow and commit individually. Group order is the
execution order. Two tickets move out of numeric order: 21 runs right after 04, and 09
runs right before 13. Both moves respect `blocked_by`.

| Group | Theme | Tickets | Delivered value |
|---|---|---|---|
| 1 | Foundation | 01, 02, 03 + [review-followups-01](../../review-followups-01/spec.md) | Revisioned data model, encrypted credentials, Draft workspaces |
| 2 | Draft lifecycle and CI | 04, 21 | Promotion and permanent Revision history; CI and Postgres gates for all later groups |
| 3 | Plugin runtime | 05, 06 | Hardened, resource-limited Plugin process; manual Collection |
| 4 | Built-in Plugins | 07, 08 | Initial RSS installation, Eject, explicit Binding upgrades |
| 5 | LLM Gateway | 10, 11, 12 | Model calls, scoped tokens, call records and metrics |
| 6 | Budgets | 09, 13, 14 | Cadences, Reader time zone, retention, daily budgets and their settings |
| 7 | Draft testing | 15, 16 | Ephemeral Draft Test Runs and cancellation |
| 8 | Publishing | 17, 18 | Articles with Model Attribution, citation retries, budget failures |
| 9 | Automated operation | 19, 20 | Scheduler, purge, periodic Model Health, end-to-end smoke tests |

Group 1 was built on a single branch before this rule existed. It was split into four
stacked PRs: 01 with review-followups-01; 02; the docs-only plan revision; and 03.

## Recommended execution order and criterion coverage

Run 04 next, then follow the PR group order above. Each implementation starts in a
fresh context using this spec and its ticket.
The dependency column records actual prerequisites, rather than forcing independent
work into an artificial serial chain.

| Ticket | Outcome | Status | Blocked by | Criteria covered |
|---|---|---|---|---|
| [01](01-scaffold-and-revisioned-data-model.md) | Scaffold the core module and the revisioned Channel/Plugin data model | done | — | AC-1, AC-5, AC-53 |
| [02](02-encrypted-credentials.md) | Envelope-encrypted Secrets and LLM Provider credentials | done | 01 | AC-23 |
| [03](03-draft-workspaces-and-compatible-migration.md) | Reader Plugin starter, Draft workspaces, and compatible migration | done | 01 | AC-60, AC-61, AC-62, AC-63, AC-64 |
| [04](04-promotion-and-permanent-revision-history.md) | Promote Drafts and select permanent Revision history | done | 03 | AC-49, AC-65, AC-66, AC-67, AC-68, AC-69, AC-81 |
| [05](05-plugin-process-runner-and-manual-collection.md) | Hardened Plugin process runner and manual Collection | todo | 02, 04 | AC-11, AC-12, AC-14, AC-15, AC-16, AC-23 |
| [06](06-plugin-resource-limits-and-pinned-runtime.md) | Plugin resource limits and pinned Python runtime | todo | 05 | AC-13, AC-50 |
| [07](07-built-in-global-identities-and-initial-installation.md) | Globally identified Built-ins, shared scope, and initial RSS installation | todo | 04, 06 | AC-4, AC-7, AC-10, AC-54 |
| [08](08-eject-and-explicit-binding-upgrades.md) | Eject Built-ins and explicitly upgrade pinned Bindings | todo | 04, 05, 07 | AC-2, AC-3, AC-8, AC-9 |
| [09](09-cadences-time-zone-and-retention.md) | Cadences, Reader time zone, and Retention Window validation | todo | 01 | AC-46, AC-47, AC-48 |
| [10](10-gateway-core-and-call-driven-model-health.md) | Gateway core, Channel Models, and call-driven Model Health | todo | 02, 05 | AC-17, AC-19, AC-34, AC-36, AC-37 |
| [11](11-gateway-tokens-and-call-metadata.md) | Scoped Gateway tokens, Plugin turns, and protected call metadata | todo | 05, 10 | AC-20, AC-21, AC-22, AC-39, AC-77, AC-78 |
| [12](12-gateway-call-records-tags-and-metrics.md) | Gateway call records, analysis tags, and Prometheus metrics | todo | 11 | AC-31, AC-33, AC-79 |
| [13](13-nested-gateway-budget-enforcement.md) | Nested daily token budget enforcement | todo | 09, 12 | AC-24, AC-25, AC-26, AC-27 |
| [14](14-budget-settings-and-defaults.md) | Budget settings, defaults, and immediate configuration changes | todo | 13 | AC-28, AC-29 |
| [15](15-foreground-draft-test-preview.md) | Ephemeral Draft Test Run with Channel context and tagged accounting | todo | 06, 11, 12, 14 | AC-70, AC-71, AC-72, AC-73, AC-80 |
| [16](16-draft-test-cancellation-and-input-stability.md) | Cancel foreground tests and preserve captured input stability | todo | 15 | AC-74, AC-75, AC-76 |
| [17](17-publish-tracer-and-safe-article-rendering.md) | Publish tracer with Model Attribution and safe Article rendering | todo | 05, 10, 12 | AC-18, AC-38, AC-42, AC-51, AC-52 |
| [18](18-citation-retries-and-publish-budget-failures.md) | Citation retries, Article rejection, and Publish budget exhaustion | todo | 13, 14, 17 | AC-30, AC-40, AC-41 |
| [19](19-scheduler-purge-and-periodic-model-health.md) | Scheduler, leases, Catch-up, retention purge, and periodic Model Health | todo | 05, 09, 10, 12, 18 | AC-6, AC-32, AC-35, AC-43, AC-44, AC-45 |
| [20](20-end-to-end-smoke-test.md) | Container smoke tests for scheduled publishing and Draft-to-Collection flow | todo | 07, 08, 16, 18, 19 | AC-57, AC-82 |
| [21](21-docs-consistency-postgres-and-core-ci.md) | ADR consistency, Postgres repository checks, and core CI | todo | 04 | AC-55, AC-56, AC-58, AC-59 |

**Coverage:** AC-1 through AC-82 are assigned, with zero uncovered criteria and zero unknown
criterion references. AC-23 is intentionally shared between completed storage ticket 02
and pending environment-isolation ticket 05; the ticket-02 report covers only its original
storage/logging portion.

**Dependency check:** no cycles or missing targets. Numeric order 01 → 02 → 03 → 04 → 05 →
06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20 → 21
is a valid topological order, and so is the PR group order 01 → 02 → 03 → 04 → 21 → 05 →
06 → 07 → 08 → 10 → 11 → 12 → 09 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20. Currently 04
and 09 are ready because their prerequisites are complete; 04 is the recommended next
ticket.

## Delivery stages and dependency splits

- **03–04:** saved Draft workspaces, compatible migration, starter, file editing,
  exact-pin validation, promotion, permanent branching history, current selection, and
  CLI/API rules. No execution or fake Test Run endpoint is claimed.
- **05–08:** restricted Plugin process execution, limits/uv, globally identified initial
  Built-ins/RSS, Eject, and explicit Binding upgrades.
- **09–14:** cadence/time-zone settings, Gateway and call-driven Model Health, scoped
  access and protected metadata, usage records/metrics, budgets, and operational settings.
- **15–16:** actual ephemeral Test Runs and complete cancellation/disconnect behavior.
  The complete Test Run feature requires both tickets, backed by the real runner,
  Gateway, health observations, accounting, and budgets.
- **17–20:** safely rendered Publish tracer, citation/budget failures, scheduling and
  periodic health/purge, then container smoke evidence for both scheduled publishing
  and the Draft-to-normal-Collection path.
- **21:** documentation/portability/CI gates, independently runnable once its stated
  prerequisite is complete.

Exact-pin validation moved out of old runtime ticket 04 into new promotion ticket 04.
The new runner is 05, so promotion does not depend on later execution. Call-driven
Model Health and Provider tests moved into new Gateway ticket 10; hourly listing checks
remain with scheduler 19. Test Runs therefore do not wait for Publish or the scheduler.

The following cohesive work was combined to keep the existing ticket count:
Eject with Binding upgrades (08); Publish with its initial safe rendering boundary (17);
scheduler with its hourly health job (19); and local ADR checks with Postgres/core CI
wiring (21). Ticket 04 has additional criteria because atomic promotion/history,
exact-pin validation, and their operational logging form one independently verifiable
Reader action. Ticket 11 similarly covers the scoped call contract and metadata
Adapter boundary. No horizontal all-models or all-endpoints ticket is introduced.

## Deferred decisions

Ticket 04's review left these open on purpose. Each one is parked where it next matters. See
[fix-review-minors-04](../../fix-review-minors-04/report.md) for the context.

| Decision | When | Options |
|---|---|---|
| Isolation level the promotion claim relies on | Ticket 21 | Pin READ COMMITTED in `create_engine_for`, or keep the documented assumption and prove it on Postgres |
| Naive `created_at` from SQLite outside `RevisionDetails` | Before ticket 09 | Shared UTC `TypeDecorator` on timestamp columns, or record why projections normalize |
| Success events (`plugin_draft.promoted`, `.deleted`) logged at flush, before commit | Next grill | Emit after commit at the surfaces, or record flush-time events in the spec/ADR |
| `plugin_revision.selection_rejected` and `plugin.not_found` not in the spec | Same grill | Amend the spec's Observability list, or fold them into listed events |
| `ImmutableRevisionError` signals a bulk update with an empty attribute list | Any refactor | Explicit `operation` value or named constructors |
| No researched standards for Typer 0.27, Pydantic 2.14, Alembic 1.20 | Next `/mobua-swe:setup` | Research and pin them in `docs/standards.md` |

## Historical pending-ticket map

This table maps **old responsibilities**, not file rename detection. Completed 01 and 02
retain their ids, files, statuses, and evidence.

| Original number / responsibility | Revised owner |
|---|---|
| 03: process runner/manual Collection | 05 |
| 04: resource limits and uv | 06; exact-pin validation moved to 04 |
| 05: Built-in installation/shared scope/RSS | 07, with supplied global identities and local-only history |
| 06: Eject/read-only Built-ins | 08; Draft/current-selection rejection also enforced in 03–04 |
| 07: Binding pinning/upgrades | 08 |
| 08: cadences/Reader time zone/retention | 09 |
| 09: Gateway core/Channel Models | 10 |
| 10: scoped tokens/Plugin turns | 11 |
| 11: usage records/metrics | 12 |
| 12: budget enforcement | 13 |
| 13: budget settings/defaults | 14 |
| 14: Publish tracer | 17 |
| 15: citation retries/Publish budgets | 18 |
| 16: scheduler/leases/Catch-up/purge | 19 |
| 17: Model Health | 10 for call-driven/on-demand health; 19 for hourly listing |
| 18: Article sanitizer | 17 |
| 19: local ADR checker | 21 |
| 20: container smoke | 20, extended to cover the Draft lifecycle |
| 21: Postgres/core CI | 21, including its local ADR-check prerequisite |

Reader Draft work is incorporated into 03–04 and 15–16. Built-in patch/release update
delivery, installation/rollback policy, and remote/full history remain explicitly deferred.

## Observability ownership

| Spec item | Owner |
|---|---|
| plugin_run.failed, news_item.rejected | 05; limit fields 06; no Draft-test emission in 15–16 |
| channel_model.unknown | 11, normal calls only; tests retain error/accounting without Channel Health |
| gateway.budget_refused | 13, trusted caller origin with test Health exception |
| gateway.call_failed | 10, with protected origin supplied by 11 |
| model_health.degraded | 10 for call/on-demand observations; 19 for hourly listing |
| article.citations_unmatched, article.rejected | 18 |
| channel_revision.rejected | Existing 01; Binding reasons 08, cadence/retention 09, Models 10 |
| collection.skipped_no_bindings, scheduler.run_deferred_by_lease, run_lease.expired | 19 |
| builtin_plugin.seeded | 07, initial globally identified installation only |
| plugin_draft.deleted | 03 |
| plugin_draft.promoted, plugin_draft.rejected | 04 |
| plugin_draft.conflict | 03 for save; 04 for promotion/current-selection confirmation |
| Four gateway metric families / bounded labels | 12; refusals incremented by 13; test consumption verified by 15 |
| No durable test output/history or test-driven Channel Health | 15–16, integrated by 20 |

## Deployment verification ownership

The numbers below refer to checklist positions in the amended spec.

| Check | Owner |
|---|---|
| 1: four Gateway metrics | 12 |
| 2: zero-Binding Collection scheduling/Health/log | 19 |
| 3: RSS Collection, restricted uid, uv | 05–07 |
| 4: env-dump isolation | 05 |
| 5: budget change/refusal/metric/no Channel Revision | 13–14 and 18 |
| 6: Provider test, Model Health, normal Channel links | 10; periodic listing 19 |
| 7: Article Model Attribution | 17 |
| 8: local ADR checker | 21 |
| 9: PR/main CI gates and broken-index failure | 21 |
| 10: invalid Draft save, rejection, atomic promotion and safe logs | 03–04 |
| 11: stale workspace conflict and history/current selection | 03–04 and 08 |
| 12: ephemeral test preview, real budgets/tags, no Channel side effects | 15, integrated by 20 |
| 13: interrupt/disconnect cleanup and retained incurred usage | 16 |
| 14: global Built-in identity, local history, read-only and Eject | 07–08 |
| 15: compatible pre-Draft migration | 03 |

Implementation evidence must report actual command results and retain a Not verified
section for unobserved deployment checks. This plan itself is documentation validation,
not evidence that these pending behaviors have been implemented.
