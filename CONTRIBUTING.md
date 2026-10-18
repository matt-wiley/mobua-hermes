# Contributing

Thanks for your interest. The project is in its design phase, so the most useful contributions right now are questions and critiques of the design.

## Before you start

- Read [`CONTEXT.md`](CONTEXT.md). It defines the domain terms (Channel, Plugin, News Item, Article, Style, ...) and lists words to avoid. Use these terms in issues, code, and docs.
- Skim [`docs/adr/`](docs/adr/) for decisions already made and the alternatives rejected.
- Track work in local ticket files under `docs/specs/`; do not create GitHub issues.

## Architecture decisions

Significant design changes get an ADR in `docs/adr/`:

- Name it `NNNN-short-title.md`, using the next free number.
- Start with a metadata block under the title: `Status:` (`Proposed`, `Accepted`, or `Superseded by ADR NNNN`), `Date:` (when accepted), and `Amends:` / `Amended by:` where they apply.
- Use the existing sections: **Context**, **Decision**, **Alternatives rejected**, **Consequences**.
- Don't rewrite an accepted ADR's decision. Supersede or amend it with a new ADR, update both ADRs' metadata, and add a short note where the change applies in the old one (see ADRs 0016 and 0018).
- Add or update its row in the [ADR index](docs/adr/README.md) by hand.
- If the change introduces or changes a term, update `CONTEXT.md` in the same pull request.

## Pull requests

- Keep each pull request focused on one change.
- Describe what changed and why, and link the related issue or ADR.
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Licensing of contributions

The project is licensed under the [AGPL-3.0](LICENSE). By submitting a contribution, you agree that it is licensed under the same terms.
