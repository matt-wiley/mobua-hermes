# Security Policy

## Supported versions

The project has no releases yet. Until it does, only the latest commit on `main` is supported.

## Reporting a vulnerability

Please don't report security issues in public issues or pull requests.

Email them to mattwiley@fastmail.com instead. Include what you found, how to reproduce it, and the impact you expect.

You should get an acknowledgement within a week. Fixes are coordinated privately and disclosed once a fix is available.

## Scope

Areas of particular interest, given the design:

- Secret storage and the Master Key (ADR 0009)
- Gateway Tokens and Channel Model scoping (ADRs 0008, 0021)
- Plugin subprocess execution and hardening (ADRs 0005, 0015, 0016, 0020)
- Reader data scoping (ADR 0007)
- Prompt injection from retrieved content, and unsafe markup in Article output

Plugins are hardened but not sandboxed (ADR 0020). A Plugin escaping its environment, OS user, or resource limits through ordinary means is in scope. Deliberately malicious Plugin code breaking out through kernel or container escapes is not.
