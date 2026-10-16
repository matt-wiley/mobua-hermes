# 0001. Channels write their own Articles

Status: Accepted
Date: 2026-10-16

## Context

Articles could be written by one shared pipeline in the Core, or by each Channel. The app's main value is output tuned to one reader's information-processing style.

## Decision

Each Channel writes its own Articles. Plugins only retrieve information; they don't write. The Core owns the Style, and Channels read it at write time.

## Alternatives rejected

- **Core writes all Articles from raw items.** One place to tune style, but makes the Core responsible for every Channel's content and history.
- **Plugins write Articles.** Puts LLM writing into every retrieval script.

## Consequences

- Style adherence happens inside each Channel.
- Channels need access to the Style.
