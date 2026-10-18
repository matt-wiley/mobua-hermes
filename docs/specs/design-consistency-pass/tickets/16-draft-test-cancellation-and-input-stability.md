---
id: design-consistency-pass-16
title: "Cancel foreground tests and preserve captured input stability"
status: todo
blocked_by: [design-consistency-pass-15]
external: null
---

# Cancel foreground tests and preserve captured input stability

## Goal
Complete foreground Test Run lifetime behavior through both CLI and API: terminate on cancellation/disconnect, revoke access, clean files, and keep running input stable while saved Drafts change.

## Criteria covered
AC-74, AC-75, AC-76

## Seams
- Pure core: execution lifetime/completion/cancellation states and exactly-once cleanup decisions.
- Edges: subprocess-tree termination, Gateway cancellation/revocation including pending turns, API disconnect, CLI interruption, private temporary cleanup.
- Capture the saved implementation/config once in memory. No long database transaction spans execution, and completion never writes captured contents back into the Draft.

## Observability
- Do not persist test output/stderr/lifecycle history. Ordinary usage already incurred survives interruption with trusted test origin.
- Actual Provider failures can update Model Health; cancellation itself is not a new Channel Health event.

## Verification
- AC-74: active explicit cancellation kills child processes and descendants, removes run directories, and makes token reuse fail while incurred usage remains.
- AC-75: actual CLI interrupt and API disconnect use the same cleanup, including a controlled pending Gateway turn; Manifest timeout remains a backstop.
- AC-76: save, promote, and delete a Draft after execution starts; original captured inputs run unchanged, usage identity stays fixed, and completion does not overwrite/recreate Draft records.
- Repeat completion/cancellation races with controlled synchronization; verify cleanup idempotence without sleeps as the primary assertion.

## Deployment verification
- Own interrupt/disconnect deployment check and stable-input/no-history aspects of Test Run verification.

## Out of scope
- Resumable/background test jobs, persistent snapshots, arbitrary cancellation of normal Channel runs, update delivery.
