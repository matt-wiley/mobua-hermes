---
id: design-consistency-pass-14
title: "Budget settings, defaults, and immediate configuration changes"
status: todo
blocked_by: [design-consistency-pass-13]
external: null
---

# Budget settings, defaults, and immediate configuration changes

## Goal
Expose operational budget configuration through the CLI with defaults on Reader/Channel/Provider settings, effective on the next Gateway call without creating Channel Revisions.

## Criteria covered
AC-28, AC-29

## Seams
- Pure core: default and unlimited settings representation.
- Edges: real settings persistence, CLI budget command, existing Gateway decisions. Keep Channel budget on its identity.

## Observability
- No new events or metrics; actual refusal uses the existing Gateway events/counters.

## Verification
- AC-28: change budget through actual CLI, check no Channel Revision was created and the next normal or test call uses the changed value.
- AC-29: defaults Channel 500,000, Reader 2,000,000, Provider uncapped; explicit unlimited round-trips.
- Reject foreign Reader setting changes and invalid input without touching saved settings.

## Deployment verification
- Own settings/no-new-Revision portion of budget deployment check. Publish refusal demonstration is 18; test consumption demonstration is 15.

## Out of scope
- Web App budget settings screens, monetary conversion, revisioning operational settings.
