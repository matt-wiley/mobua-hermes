# Architecture decision records

Decisions that are hard to reverse, surprising without context, and a real trade-off. See [CONTRIBUTING](../../CONTRIBUTING.md#architecture-decisions) for the format. Update this index whenever an ADR is added, amended, or superseded.

| # | Decision | Status | Amended by |
|---|---|---|---|
| [0001](0001-channels-write-articles.md) | Channels write their own Articles | Accepted |  |
| [0002](0002-channel-schedules-core-pulls.md) | Channels run Collection and Publishing schedules; the Core pulls | Accepted |  |
| [0003](0003-channels-own-their-history.md) | Channels own their own history | Accepted |  |
| [0004](0004-own-news-item-schema.md) | News Items use the app's own RSS-shaped schema | Accepted |  |
| [0005](0005-plugins-run-as-subprocesses.md) | Plugins run as subprocesses | Accepted | 0022 |
| [0006](0006-single-container-with-seams.md) | Ship as one container, with seams for scaling out | Accepted |  |
| [0007](0007-all-data-scoped-to-a-reader.md) | All data is scoped to a Reader; Channels have one owner | Accepted | 0019 |
| [0008](0008-llm-access-via-core-gateway.md) | Channels and Plugins reach LLMs only through the Core's LLM Gateway | Accepted | 0020, 0021 |
| [0009](0009-secrets-envelope-encryption.md) | Secrets use envelope encryption with a deploy-time Master Key | Accepted |  |
| [0010](0010-enforced-citations.md) | Citations are enforced through the Plugin contract and validated after writing | Accepted |  |
| [0011](0011-python-fastapi-sveltekit-static.md) | Python + FastAPI core; SvelteKit web app served by FastAPI | Accepted | 0022 |
| [0012](0012-own-thin-llm-gateway.md) | Build our own thin LLM Gateway over existing provider libraries | Accepted | 0021, 0023, 0024 |
| [0013](0013-sqlite-default-postgres-ready.md) | SQLite by default, Postgres-ready, one shared database | Accepted |  |
| [0014](0014-own-db-driven-scheduler.md) | Own database-driven scheduler with per-Channel leases | Accepted |  |
| [0015](0015-plugin-package-contract.md) | Plugins have a TOML manifest and are invoked over stdin/stdout | Accepted | 0016 |
| [0016](0016-config-and-plugins-as-revisioned-records.md) | Channels and Plugins are database records with immutable revisions; Plugin code is data | Accepted | 0018, 0024 |
| [0017](0017-service-layer-with-api-and-cli-surfaces.md) | One Python package: a service layer with API and CLI surfaces | Accepted |  |
| [0018](0018-plugin-bindings-pin-plugin-revisions.md) | Channels use Plugins through Plugin Bindings pinned to a Plugin Revision | Accepted | 0019, 0024 |
| [0019](0019-built-in-plugins-are-shared-and-ejectable.md) | Built-in Plugins are shared, system-owned, and ejectable | Accepted | 0024, 0025 |
| [0020](0020-plugin-runs-hardened-not-sandboxed.md) | Plugin Runs are hardened at the OS level, not sandboxed | Accepted |  |
| [0021](0021-channel-models.md) | Channels configure named Channel Models; Plugins reach LLMs only through them | Accepted | 0024 |
| [0022](0022-plugin-runtimes-and-pinned-inline-dependencies.md) | v1 Plugins run on Python or shell, with pinned inline dependencies run by uv | Accepted |  |
| [0023](0023-llm-usage-budgeted-recorded-attributed.md) | LLM usage is budgeted, recorded, and attributed | Accepted | 0024 |
| [0024](0024-plugin-drafts-and-permanent-revision-history.md) | Plugins have disposable Drafts and permanent Revision trees | Accepted | 0025 |
| [0025](0025-built-in-plugin-identities-and-global-lineage.md) | Built-in Plugins preserve global identities and development lineage | Accepted |  |
