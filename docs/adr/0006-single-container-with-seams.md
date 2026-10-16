# 0006. Ship as one container, with seams for scaling out

Status: Accepted
Date: 2026-10-16

## Context

The system is self-hostable: it should run on a laptop (web app on localhost) or on a server, without requiring a server. Future scale, and possibly multiple users, should not require a rewrite.

## Decision

v1 ships as a single container. The server process runs each Channel as an internal worker whose data is logically separate: rows in the shared database scoped by Channel and Reader (ADR 0013). Plugins run as subprocesses inside the container. The Core and Channels interact only through defined interfaces, not shared internals, so Channels can later move into separate processes or containers:

1. Aggregation from Inboxes (its shape is set by the Channel contracts grill)
2. Style reads
3. LLM Gateway calls (ADRs 0008, 0021)
4. Secret delivery to Plugin Runs (ADR 0009)
5. Run triggers from the shared scheduler (ADR 0014)
6. Channel Health reports
7. Channel configuration: Revisions and Plugin Bindings edited through the Web App and CLI (ADRs 0016, 0018)

## Alternatives rejected

- **One container per Channel.** Strong isolation and independent scaling, but too many moving parts for a single reader, and creating a Channel would mean provisioning infrastructure.

## Consequences

- One `docker run` is enough to use the app.
- Interfaces between Core and Channels must stay network-ready even while calls are in-process.
