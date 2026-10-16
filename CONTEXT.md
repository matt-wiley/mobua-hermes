# Context

Glossary for the personal news app: an RSS-style aggregator with custom retrieval (Plugins) and custom output style (Style).

## Terms

- **Reader**: A user of the app. v1 has one, but all data is scoped to a Reader.
- **Channel**: Owned by one Reader, who creates and configures it (possibly with custom code); there are no built-in Channels. Pulls information from Sources via its Plugin Bindings, keeps it in its Feed, and writes Articles into its Inbox. Runs two schedules: a Collection cadence and a Publishing cadence.
- **Plugin**: A named retrieval definition, owned by one Reader unless it is a Built-in Plugin: an RSS feed, a scraper, or a custom script. Has Revisions; Channels use a specific one through a Plugin Binding. Runs as a subprocess and outputs News Items.
- **Built-in Plugin**: A Plugin that ships with the app (e.g. RSS). System-owned, shared by all Readers, and read-only.
- **Eject**: Copying a Built-in Plugin into a new Plugin the Reader owns, with no link back to the original.
- **Plugin Binding**: A Channel Revision's use of one exact Plugin Revision, with that Channel's config for it, validated against that Revision's config schema.
- **Plugin Manifest**: A Plugin's TOML declaration: name, command, config schema, required Secrets, timeout. Stored in the database.
- **Revision**: An immutable snapshot of a Channel or Plugin. A Channel Revision holds its configuration and Plugin Bindings; a Plugin Revision holds its Manifest and code, and records who created it. Edits create new Revisions; Collections, Publishes, and Articles record the Revisions they used.
- **Plugin Run**: One subprocess execution of a Plugin Binding's Plugin Revision during a Collection. Keeps its stderr log, capped in size. Killed if it exceeds its timeout. Ends in success or failure; only successful runs' News Items are ingested.
- **Source**: An upstream origin (feed, site, API, search) a Plugin reads from.
- **News Item**: One item a Plugin produces from what it found, in the app's own RSS-shaped schema (stable id, title, link, published time, summary, full content, Source References, free-form metadata). The id is the Feed's dedup key.
- **Source Reference**: Where a News Item's information came from: URL, title, publisher, retrieved-at. Every News Item needs at least one, original reporting first; items without one are rejected at ingest.
- **Feed**: A Channel's internal, short-term store of News Items. Items are marked used once an Article covers them and dropped after the Retention Window.
- **Retention Window**: How long a Channel keeps News Items. Beyond it, past Articles are the record of what was seen.
- **Collection**: On the Collection cadence, a Channel starts a Plugin Run for each of its Plugins in parallel. Complete when every Plugin Run has ended and the Channel has ingested the News Items received. Marked partial if any Plugin Run failed.
- **Catch-up**: When a Channel wakes after missing scheduled runs, it runs each overdue cadence once instead of replaying every missed slot, Collection before Publish.
- **Run Lease**: A Channel's database lock held while a Collection or Publish is in progress. A run that comes due meanwhile waits until the lease is released, rather than being dropped; the lease expires after a timeout.
- **Channel Health**: A Channel's record of problems that need the Reader's attention: failed Plugin Runs, rejected News Items, refused Channel Model calls, missing Plugin Bindings. Shown in the Core so a broken Channel gets noticed; links to the logs of the Plugin Runs it flags.
- **Topic**: A group of related unused News Items that a Channel decides to cover together.
- **Article**: Written by a Channel about one Topic, from News Items in its Feed, with awareness of its own past Articles. Can continue a story from a past Article. Must cite the original upstream reporting it draws on.
- **Citation**: A footnote in an Article pointing to original upstream reporting (not to an internal News Item). Built from the Source References of the News Items used, and copied into the Article so it outlives them. Every Citation must match a Source Reference; anything else fails validation.
- **Publish**: On the Publishing cadence, a Channel groups unused News Items into Topics, checks its past Articles for context, and writes one Article per Topic into its Inbox. May produce no Articles.
- **Inbox**: A Channel's store of Published Articles, waiting for the Core.
- **Aggregation**: The Core requesting Articles from Channels' Inboxes.
- **Core**: The central app experience, as a design concept rather than code: surfaces all Channels' Inboxes to the reader in aggregated form, and owns the Style. Never merges or dedupes across Channels; overlap is the reader's to manage through Plugin configuration.
- **Service layer**: The central shared code: domain logic for Channels, the Core, the scheduler, and the LLM Gateway, independent of HTTP or terminals. The API and CLI are thin surfaces over it.
- **Web App**: The Core's own UI. For reading Articles, giving Feedback, editing the Style, reviewing Style Proposals, configuring Channels, and checking Channel Health. Feedback is only available here.
- **Syndication Feed**: The Core's aggregated output as RSS, so the reader can read in any third-party feed reader. Read-only; no Feedback.
- **LLM Provider**: A hosted or local LLM service a Reader connects in the Core. A Reader can add several.
- **Model**: A specific model from one of the Reader's LLM Providers that the Reader has enabled. Channels use them as Channel Models. Channels and Plugins never hold LLM keys.
- **Channel Model**: A Model in a Channel's configuration under a name the Channel owner chooses (e.g. `writer`, `grouper`). Each LLM step of Publish uses one; steps inherit the writing step's Channel Model unless set. Plugins can reach a Model only through its Channel Model name.
- **Model Health**: The Reader's record of whether each LLM Provider and Model is reachable and working. Fed by real Gateway calls, a periodic check, and on-demand tests; Channels using an unhealthy Model link to it from Channel Health.
- **Model Attribution**: The record on an LLM-produced output (Article, Style Proposal, Plugin Run) of which Models were used for which steps. Copied onto the output so it outlives call records.
- **LLM Gateway**: The Core's small internal API through which Channels and Plugins call Models by Channel Model name. Plugin Runs reach it with a Gateway Token. One call: messages in, text or schema-validated JSON out, with token usage.
- **Gateway Token**: A short-lived credential a Plugin Run uses to call the LLM Gateway, scoped to its Channel's Channel Models. Never a real provider key.
- **Provider Adapter**: The Gateway's translation layer for one family of LLM Providers (e.g. OpenAI-compatible, Anthropic).
- **Secret**: A Source credential (login, API key) a Plugin needs. Stored encrypted by the Core, per Reader, and injected into a Plugin Run as environment variables. Never in Plugin config or code.
- **Data Key**: A Reader's own encryption key for their Secrets and LLM Provider credentials, stored encrypted by the Master Key.
- **Master Key**: The deploy-time key that encrypts each Reader's Data Key. Supplied to the container, never stored with the data.
- **Style**: A living document in the Core, one per Reader, describing how that Reader best takes in information. Channels read it when writing Articles. Hand-edited by the reader and informed by Feedback, like a memory document for an LLM harness.
- **Feedback**: The reader's note on a single Article about what did or didn't work. Input to the Style.
- **Style Proposal**: A diff to the Style that the Core agent drafts from accumulated Feedback on a cadence. The reader accepts, denies, or redirects it.
- **Core agent**: The LLM-driven part of the Core that drafts Style Proposals, using one Model the Reader chooses. Runs on the shared scheduler.

## Avoid

- "Metasource", "News Agent", "Newsroom": use Channel.
- "Subscribe to" a Channel: the reader creates Channels; there are no built-in ones.
- "Inbox" for unwritten source information; that's the Feed.
- "Plugin" for the whole Channel; a Plugin only retrieves.
- "Plugin instance" or "Plugin config" for a Channel's use of a Plugin; that's a Plugin Binding.
- "Version" for a Channel or Plugin snapshot; use Revision.
- "Fork" for a Reader's copy of a Built-in Plugin; it's Ejected, with no lineage kept.
- "Profile" when you mean Style.
- "Refresh" or "update" for a Collection.
- "Core" for the service layer; the Core is the central app experience (design), the service layer is the shared code.
- "Core" for the server process or container; say "server process" or "app".
- "API key" for how a Plugin reaches LLMs; Plugins only ever hold a Gateway Token.
