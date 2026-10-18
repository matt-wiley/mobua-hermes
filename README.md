# mobua-hermes

> **Working title.** The project doesn't have a final name yet; the repo and the `news` Python package may be renamed.

A self-hostable personal news app: an RSS-style aggregator with custom retrieval and LLM-written output tuned to how one reader best takes in information.

- **Channels** you create pull from Sources through **Plugins** (an RSS feed, a scraper, or a custom script in any language).
- Each Channel groups what it finds into **Topics** and writes **Articles** in your **Style**, a living document refined by your **Feedback**.
- Every Article cites the original upstream reporting it draws on, and any Citation that doesn't match a Source Reference fails validation.
- The **Core** aggregates all Channels for reading in its Web App or any feed reader.

## Status

Design phase. There is no code yet; the architecture is captured in the docs below.

## Docs

- [`CONTEXT.md`](CONTEXT.md): glossary of domain terms. Start here.
- [`docs/adr/`](docs/adr/README.md): architecture decision records, with an index of their status and amendments.
- [`docs/credentials.md`](docs/credentials.md): Master Key setup and encrypted Secret / Provider CLI commands.

Planned stack: Python + FastAPI, SvelteKit (static), SQLite by default with Postgres support, shipped as a single container.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md). Report vulnerabilities as described in [SECURITY.md](SECURITY.md).

## License

[GNU Affero General Public License v3.0](LICENSE). If you run a modified version as a network service, you must offer its users the corresponding source code.
