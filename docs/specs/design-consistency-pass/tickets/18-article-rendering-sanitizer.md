---
id: design-consistency-pass-18
title: Allowlist sanitizer for rendering Article text
status: todo
blocked_by: [design-consistency-pass-01]
external: null
---

# Allowlist sanitizer for rendering Article text

## Goal
Provide the service-layer function that renders Article text for display through an allowlist sanitizer.

## Criteria covered
AC-52

## Seams
- Pure core: the sanitizer function (no I/O).

## Observability
- None.

## Verification
- AC-52: `<script>`, event handlers, and `javascript:` URLs removed; allowlisted formatting kept; tests with a set of known XSS payloads.

## Out of scope
- Web App and Syndication Feed rendering (not yet specified); they will call this function.
