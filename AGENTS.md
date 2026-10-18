# Repository Guidelines

## Agent Session Setup: mobua-swe Skills

At the start of every session in this repository, discover the installed Claude Code `mobua-swe` skills and make them available as local, file-backed workflows, even when they are absent from the session's built-in skill catalog:

1. Resolve `mobua-swe@mobua-plugins` in `~/.claude/plugins/installed_plugins.json` and use its `installPath` as the plugin root. The current installation is `~/.claude/plugins/cache/mobua-plugins/mobua-swe/0.1.0/`. If the registry entry is unavailable, look under `~/.claude/plugins/cache/mobua-plugins/mobua-swe/` and verify the plugin's manifest before selecting an installation.
2. Read the plugin's `README.md` and the `name` and `description` frontmatter of every `skills/*/SKILL.md` to build the session's skill inventory. Read `docs/mobua-swe.md` for repository configuration.
3. Recognize `/mobua-swe:<name>` requests by reading and following `<plugin-root>/skills/<name>/SKILL.md`. Available skills currently include `which`, `setup`, `grill`, `to-spec`, `to-tickets`, `implement`, `code-review`, `fix`, `refactor`, `spike`, `research`, `tdd`, and `standards`. Load `standards` when planning, writing, or reviewing code and `tdd` before changing production code. Invoke other workflows when requested; discovery alone does not start them.
4. Resolve supporting references relative to the skill directory and `${CLAUDE_PLUGIN_ROOT}` to the resolved plugin root. Adapt Claude-specific tool names to the available equivalents while preserving the workflow's requirements. Reading skills does not activate Claude Code hooks.

If the installation or a requested skill is missing, report the exact missing path and do not claim it is loaded. User instructions and higher-priority session rules take precedence over skill instructions.

## Project Structure & Module Organization

The `news` Python package lives in `src/news/`. Business logic and persistence belong in `service/`; `cli/` exposes Typer commands, and `api/` contains the FastAPI app. Packaged Alembic migrations live in `src/news/migrations/`. Tests mirror these boundaries under `tests/service/`, `tests/cli/`, and `tests/api/`, with shared fixtures in `tests/conftest.py`.

Read `CONTEXT.md` for domain terminology, `docs/adr/` for architecture decisions, and `docs/standards.md` for detailed coding rules. Implementation specifications and review evidence live in `docs/specs/`. The SvelteKit frontend is planned; no `web/` directory exists yet.

## Build, Test, and Development Commands

Use Python 3.14+ and uv:

- `uv sync`: install dependencies and development tools.
- `uv run news --help`: explore the local CLI.
- `uv run news db upgrade`: apply database migrations.
- `uv build`: build the source distribution and wheel.
- `uv run pytest`: run the complete test suite.
- `uv run pytest tests/service/test_channels.py`: run a focused test file.
- `uv run ruff check .` and `uv run ruff format --check .`: check lint and formatting; use `uv run ruff format .` to format.
- `uv run pyright`: run strict type checking.
- `uv run lint-imports`: verify architectural import boundaries.

## Coding Style & Naming Conventions

Use four-space indentation, 100-character lines, type annotations, `snake_case` functions/modules, and `PascalCase` classes. Follow Ruff's formatting and import ordering. API and CLI modules call the service layer; they must not import each other, and services must import neither. Keep database behavior portable between SQLite and PostgreSQL and enforce Reader/Channel scope in services.

## Testing Guidelines

Use pytest with `test_*.py` files and `test_*` functions. Reuse temporary database fixtures, which apply migrations. Add regression tests for changed behavior, including rejection paths and scope boundaries. Warnings fail tests, and markers are strict. No numeric coverage threshold is configured.

## Commit & Pull Request Guidelines

Recent commits use a scope or ticket prefix, such as `review-followups-01-06: guard immutable revisions`. Write concise, action-oriented subjects. Open an issue before substantial work. Ship each PR group in a spec's tickets README (for example `docs/specs/design-consistency-pass/tickets/README.md`) as its own branch and PR; never accumulate several groups on one branch. Keep PRs focused; explain what changed and why, link the issue or ADR, and report validation. Follow the PR template: update terminology and tests where applicable. Significant design changes require a new or amending ADR and an updated ADR index.

## Security & Configuration

Follow `docs/credentials.md` for Master Key setup. Never log keys or credential values; store credentials through the encrypted service APIs. Report vulnerabilities according to `SECURITY.md`.
