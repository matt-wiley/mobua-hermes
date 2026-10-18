# 0024. Plugins have disposable Drafts and permanent Revision trees

Status: Accepted
Date: 2026-10-17
Amends: ADRs 0012, 0016, 0018, 0019, 0021, 0023
Amended by: ADRs 0025, 0026

## Context

Editing a Plugin currently creates an immutable Revision immediately. Readers need to try
several implementations independently before choosing one to make available to Channels.
Treating experiments as Revisions would mix unfinished work with runnable configuration.
Keeping only one working copy would prevent parallel experiments from the same starting point.

## Decision

Built-in lifecycle amendment: ADR 0025 replaces the Built-in starter/local lineage rules
below with stable global UUIDs and development lineage. Reader-owned Plugin rules and
Eject initialization remain in effect.

- A Plugin can have many mutable **Plugin Drafts**. Each copies its Manifest and code from
  exactly one parent Plugin Revision belonging to that Plugin.
- Every new Plugin, Reader-created or Built-in, starts with a valid starter as Revision 1.
  It emits no News Items and exits successfully. This is the root of the Revision tree.
- **Promote** validates a Draft, including its Manifest and required exact dependency pins,
  copies its contents into a new immutable Revision, makes that Revision current, and
  deletes the Draft atomically. Failure preserves the Draft and leaves Revisions and the
  current pointer unchanged. Further editing starts with a new Draft from a Revision.
- The new Revision records the Draft's parent Revision. Promotion from an older Revision
  is allowed with explicit confirmation that the new Revision will replace the current
  one. There is no merge. Sibling Drafts remain unchanged.
- Readers can permanently delete their unpromoted Drafts. Promoted Drafts are deleted
  because the new Revision holds their contents.
- Plugin Revisions are never archived or deleted. Their complete Manifest, code, ancestry,
  and metadata remain available in the Plugin Revision History. A Reader can view their
  Plugin's history and select any Revision as current at any time.
- Selecting a Revision as current does not create a Revision or move Channel Bindings.
  Bindings remain pinned; moving them creates a Channel Revision and validates config
  under ADR 0018. Promotion also leaves Bindings unchanged.
- Built-in Plugins remain system-owned and read-only to Readers under ADR 0019. The system
  manages their Revisions. Readers Eject a Built-in to obtain an editable Plugin of their
  own. Built-ins receive the starter root before their shipped implementation.
- Eject creates the new Plugin's starter Revision 1, then copies the Built-in's current
  Manifest and code into Revision 2 with Revision 1 as its parent, making Revision 2 current.
  The exact copy is immediately usable without a Draft promotion step. Its history has
  no link to the Built-in; existing Channels are not moved automatically.
- This Draft process applies only to Plugins. Channel edits continue to create immutable
  Channel Revisions directly.
- Shared services expose the complete workflow through CLI and API; Web App screens follow
  when the frontend exists. CLI editing uses explicit export/edit/save of local files.
  (Workspace file set: amended by ADR 0026, which limits it to the Manifest and `main.py`.)
  Test and Promote operate on the saved database Draft; deleting it leaves local files alone.
- Draft exports carry a version marker. Save and Promote require the expected version;
  stale requests fail with a conflict and change neither Drafts nor Revisions/current pointers.
- Migration preserves existing Reader-owned Plugin Revisions, ids, numbering, contents,
  current selections, and Bindings. Starter initialization applies only to newly created
  Reader-owned Plugins. Do not insert artificial starters or invent unrecorded ancestry.
- Draft Test Runs are ephemeral checks using a selected Reader-owned Channel and temporary
  Plugin config. Validate before execution and use the normal launcher hardening and limits.
  Show output, validation errors, and stderr without ingesting News Items or changing Channel
  configuration. Do not retain Test Run history or duplicate Manifest/code snapshots. Network
  and LLM calls are real, and ordinary Gateway budgets, call records, and metrics still apply.
- Test Runs may execute alongside the selected Channel's Collection or Publish. They do
  not take its Run Lease or change schedules; normal process limits and shared budgets apply.
- Test Runs execute in the foreground. Cancellation, CLI interruption, or API disconnect
  stops execution, revokes Gateway access, and cleans temporary files. There is no durable
  background test job to retrieve or resume; already incurred Gateway usage remains recorded.
- Gateway calls accept extensible metadata, stored with the ordinary usage record. The Gateway
  automatically adds `test_run: true` and Plugin/Draft identifiers for Test Run calls and
  protects the test marker from caller overrides. Additional caller-supplied tags are allowed.
  Metadata is separate from prompt text and forwarded to Providers that support it. Local
  tagging remains available when a Provider does not support forwarding. Tags do not become
  arbitrary Prometheus labels; ADR 0023's existing metric label policy remains in force.
- Draft Test Runs never drive Channel Health, including for unknown Channel Model names
  or budget refusals. Their errors are shown in test results; Gateway outcomes and tags
  remain in ordinary usage accounting. Real Provider failures still update Model Health.
  Plugin-related Channel Health continues to reflect normal runs of promoted Revisions.

## Alternatives rejected

- **Revisions with draft and promoted states.** Weakens immutability wherever Revisions
  are used and makes unfinished implementations look bindable.
- **One Draft per Plugin.** Prevents independent experiments from a shared parent.
- **Editor-local Drafts.** Lose work with browser storage and do not follow the Reader
  across devices.
- **Parentless initial Drafts.** Require a special ancestry rule; a valid starter gives
  every Plugin a usable root instead.
- **Archiving or deleting Revisions.** Adds lifecycle rules without helping the desired
  permanent, selectable history.
- **Retaining promoted Drafts.** Duplicates contents already preserved in the new Revision.
- **Merging on promotion.** Changes the experiment the Reader chose to promote.

## Consequences

- Editing and making an implementation current are separate operations.
- Revision ancestry is a tree; revision order and current selection do not imply ancestry.
- Draft storage is mutable and disposable; Revision storage is immutable and permanent.
- New Plugins have a starter Revision before their first custom implementation. Built-in
  seeding must also account for this root.
- Existing creation interfaces need to adopt starter initialization and separate Draft
  operations. Migration must preserve existing Revisions and Bindings as specified above.
- Detailed Draft execution, surface behavior, staging, and verification are recorded in the
  [Plugin drafts grill](../specs/plugin-drafts/grill.md).
- The confirmed Draft design is implemented through the amended existing
  [design-consistency spec](../specs/design-consistency-pass/spec.md) and its
  [reordered pending tickets](../specs/design-consistency-pass/tickets/README.md),
  rather than a separate spec or ticket set.
