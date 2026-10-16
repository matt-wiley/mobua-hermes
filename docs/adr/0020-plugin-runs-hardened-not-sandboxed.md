# 0020. Plugin Runs are hardened at the OS level, not sandboxed

Status: Accepted
Date: 2026-10-16
Amends: ADR 0008

## Context

Plugins may be Reader-written or third-party code (ADR 0008) and run as subprocesses inside the app's container (ADRs 0005, 0006). Without stated isolation, a Plugin Run could inherit the server process's environment (which may hold the Master Key, ADR 0009), read the database file on the data volume, or read the server process's or other Plugin Runs' process state and files. ADR 0008's guarantee that Plugins never see real API keys depends on preventing this.

## Decision

Every Plugin Run is hardened:

1. **Clean environment.** The subprocess gets only minimal basics (`PATH`, locale), its declared Secrets, and the LLM Gateway URL and scoped token. Nothing is inherited from the server process's environment.
2. **Separate unprivileged OS user.** Plugin Runs execute as a dedicated user with no read access to the data volume, the Master Key, or the app's files, each in its own temporary directory.
3. **Resource limits.** CPU time, memory, and file-size limits, in addition to the Manifest timeout (ADR 0015).

Network access is allowed; Plugins need it to retrieve, and Gateway tokens are already scoped and short-lived.

**Trust model:** this hardening prevents accidental leaks and casual access. It is not a sandbox against deliberately malicious code; kernel and container escapes are out of scope. Readers should only run Plugins they trust.

## Alternatives rejected

- **Namespace sandbox (bubblewrap, nsjail, gVisor).** Real isolation, but inside Docker it typically needs extra privileges or a special runtime, breaking the single `docker run` goal (ADR 0006). Revisit if public Plugin sharing is built.
- **No isolation, documented trust only.** Simplest, but a buggy Plugin dumping its environment would leak the Master Key.

## Consequences

- The container image needs a second OS user, and the server process needs the privilege to launch processes as it.
- ADR 0008's guarantee becomes: Plugins are never given real keys and cannot read the app's data or the server process's environment.
- A future sandbox can be added behind the same subprocess launch seam without changing the Plugin contract (ADR 0015).
