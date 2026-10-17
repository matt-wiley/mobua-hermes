# Standards

Pinned snapshot written by `/mobua-swe:setup` on 2026-10-16. Each section below was copied from the user-level standards library (`~/.config/mobua-swe/standards/`) at the version noted. Repo-specific overrides are at the end and take precedence.

Refresh it by re-running `/mobua-swe:setup` when a module crosses a major version.

| Section | Library entry | Coverage | Composed from |
|---|---|---|---|
| Python | `python.md` | [3] | Base @ 3.14 (2026-10-16) |
| FastAPI | `fastapi.md` | [0] | Base @ 0.143 (2026-10-16) |
| SQLAlchemy | `sqlalchemy.md` | [2] | Base @ 2.1 (2026-10-16) |
| TypeScript | `typescript.md` | [6] | Base @ 6.0 (2026-10-16) |
| SvelteKit + Svelte 5 | `sveltekit.md` | [3] | Base @ 3.1 / Svelte 5.57 (2026-10-16) |


## Python standards

### Base (researched at 3.14, 2026-10-16)

#### Annotations and typing
- Write forward references unquoted and do not add `from __future__ import annotations` to new code. Why: 3.14 defers annotation evaluation (PEP 649/749); the future import is now deprecated and slated for removal after 3.13's EOL (2029). Source: https://docs.python.org/3.14/whatsnew/3.14.html (Porting: `from __future__ import annotations`)
- Inspect annotations at runtime with `annotationlib.get_annotations()`, not `__annotations__`. Why: deferred annotations may reference not-yet-defined names; `annotationlib` offers `VALUE`/`FORWARDREF`/`STRING` formats. Source: https://docs.python.org/3.14/whatsnew/3.14.html (PEP 649)

#### Syntax
- Use t-strings (`t"..."`, PEP 750) wherever static and interpolated parts must stay separate (SQL, shell, HTML); never pass a `Template` where a `str` is expected. Why: a t-string yields `string.templatelib.Template`, not `str`, so sanitizing consumers can treat interpolations differently. Source: https://docs.python.org/3.14/whatsnew/3.14.html (PEP 750)
- Never `return`/`break`/`continue` out of a `finally` block; run tests with warnings as errors so the `SyntaxWarning` fails CI. Why: PEP 765 makes it a warning because it silently swallows exceptions. Source: https://docs.python.org/3.14/whatsnew/3.14.html (PEP 765)
- Pick one style for multi-exception `except` clauses per repo. Unparenthesized `except A, B:` (PEP 758) is valid only on 3.14+ and only without `as`. Source: https://docs.python.org/3.14/whatsnew/3.14.html (PEP 758)

#### Concurrency
- Do not rely on the GIL for atomicity; guard shared mutable state with locks. Why: the free-threaded build is officially supported (PEP 779) and libraries increasingly ship `3.14t` wheels. Source: https://docs.python.org/3.14/whatsnew/3.14.html (PEP 779)
- Choose the asyncio event loop with `asyncio.run(..., loop_factory=...)` or `asyncio.Runner`; do not use event-loop policies. Why: the policy system is deprecated, removal in 3.16. Source: https://docs.python.org/3.14/whatsnew/3.14.html (Deprecated: asyncio)
- Use `inspect.iscoroutinefunction`, not `asyncio.iscoroutinefunction`. Why: deprecated, removal in 3.16. Source: same.
- Pass picklable arguments explicitly to `multiprocessing`/`concurrent.futures` workers; request `get_context("fork")` only deliberately. Why: Linux now defaults to `forkserver` (macOS/Windows already `spawn`), breaking code that relied on inherited globals. Source: https://docs.python.org/3.14/whatsnew/3.14.html (multiprocessing)

#### Standard library
- Use `uuid.uuid7()` for new time-ordered identifiers. Why: RFC 9562 v7 UUIDs sort by creation time, which suits database keys. Source: https://docs.python.org/3.14/whatsnew/3.14.html (uuid)
- Prefer `Path.copy()`, `copy_into()`, `move()`, `move_into()` over `shutil` for path-based file operations. Source: https://docs.python.org/3.14/whatsnew/3.14.html (pathlib)
- Use `open()`, not the deprecated `codecs.open()`. Source: https://docs.python.org/3.14/whatsnew/3.14.html (Deprecated: codecs)
- Do not depend on garbage-collector timing. Why: 3.14.0–3.14.4 shipped an incremental GC that 3.14.5 reverted. Source: https://docs.python.org/3.14/whatsnew/3.14.html (gc)

## FastAPI standards

FastAPI is still on 0.x; the version unit is the 0 series. Re-research when 1.0 ships, and read "Breaking Changes" sections in release notes on every minor upgrade (minors do break).

### Base (researched at 0.143, 2026-10-16)

#### Platform
- Use Pydantic v2 only. Why: `pydantic.v1` support was dropped in 0.128.0; the floor is `pydantic>=2.9`. Source: https://fastapi.tiangolo.com/release-notes/ (0.128.0, 0.135.2)
- Python 3.10+ is required (3.9 dropped in 0.129.0); free-threaded 3.14t is supported from 0.136.0. Source: same.

#### Routes and dependencies
- Declare parameters and dependencies with `Annotated[...]`, and group related query, header or cookie parameters into a Pydantic model (`Annotated[Model, Query()]`). Source: https://fastapi.tiangolo.com/release-notes/ (0.115.0)
- Give path operations a Pydantic return type or `response_model`. Why: since 0.130.0, responses are serialized by Pydantic in Rust when a return type is present. Source: same (0.130.0)
- Do not use `ORJSONResponse` or `UJSONResponse`. Why: deprecated in 0.131.0, since the Pydantic serializer supersedes them. Source: same (0.131.0)
- Use `scope="request"` on `yield` dependencies that must clean up before the response is sent, such as DB sessions that must commit first. Source: same (0.121.0)
- Use the `lifespan` context manager for startup and shutdown, not `on_event`. Why: `on_event` survives only as a backwards-compatibility shim for Starlette 1.0. Source: same (0.128.3, 0.133.0)
- Routers are kept by reference (0.137.0): routes added after `include_router` are reflected, and router-level dependencies, exception handlers and middleware are supported. Source: same (0.137.0)
- Send JSON request bodies with `Content-Type: application/json`. Why: `strict_content_type` checking became the default in 0.132.0. Source: same (0.132.0)

#### Serving a built frontend
- Serve a static SPA build with `app.frontend("/", directory=...)` rather than hand-mounting `StaticFiles` with a catch-all route. Path operations always take precedence. The fallback page is served only to `GET`/`HEAD` requests that accept HTML. Missing assets return 404. `check_dir="auto"` fails at startup outside development if the directory is missing. App and router dependencies apply, for example cookie auth. Source: https://fastapi.tiangolo.com/tutorial/frontend/ (added 0.138.0–0.141.0)

#### Observability
- OpenTelemetry is native as of 0.142.0. Automatic exporter setup from `OTEL_*` variables is opt-in since 0.143.0, via `FastAPI(telemetry={"auto_configure": True})` or `FASTAPI_OTEL_AUTO_CONFIGURE=true`. Source: https://fastapi.tiangolo.com/release-notes/ (0.142.0, 0.143.0)

## SQLAlchemy standards

### Base (researched at 2.1, 2026-10-16)

The 2.0 typed ORM style (`DeclarativeBase`, `Mapped[...]`, `mapped_column()`, `select()` with `Session.execute()`) is assumed as the baseline. These rules record what 2.1 changes on top of it.

- SQLAlchemy 2.1 requires Python 3.11 or later; 3.10 was dropped in August 2026. Source: https://github.com/sqlalchemy/sqlalchemy/blob/main/doc/build/changelog/migration_21.rst ("Python version compatibility starts at version 3.11")
- The asyncio extension needs `sqlalchemy[asyncio]`, because greenlet is no longer installed by default. Source: same ("Asyncio greenlet dependency no longer installs by default")
- Autoflush now runs before every execution, including `text()` and Core statements. Use `with session.no_autoflush:` where a flush must not happen yet. Source: same ("Session autoflush behavior simplified to be unconditional")
- For raw SQL on Python 3.14+, prefer `tstring(t"...")` over `text()` with manual binds. Interpolated Python values become bound parameters and SQLAlchemy expressions are embedded. Never build SQL with f-strings. Source: same ("Template String (t-string) Support")
- Use `unmapped_column()` instead of the deprecated `exclude_properties`. Source: same.
- Mapped dataclass defaults are now served by descriptors rather than set in `__dict__`, so code must not inspect `obj.__dict__` for defaults. Source: same ("ORM Mapped Dataclasses no longer populate implicit default")
- `filter_by()` now searches every FROM entity and raises an error on ambiguous names. Use explicit `where()` in multi-entity queries. Source: same (``filter_by()`` section)
- `Row` types use PEP 646 (`Select[int, str]` rather than `Select[Tuple[int, str]]`). Update type annotations accordingly. Source: same (``Row`` section)
- The PostgreSQL URL `postgresql://` now defaults to psycopg 3. Depend on `psycopg`, not `psycopg2`. Source: same ("Default PostgreSQL driver changed to psycopg")
- SQLite has a `JSONB` type (SQLite 3.45 or later). When code must stay portable to Postgres, keep the generic `JSON` type unless the binary format is needed. Source: same ("Added JSONB JSON format for SQLite")
- Alembic (1.20 at research time) is the migration tool. No version-specific rules have been researched yet.

## TypeScript standards

### Base (researched at 6.0, 2026-10-16)

- TS 6.0 defaults to `strict: true`, `module: esnext`, `target` set to the latest ES (es2025), `types: []`, `rootDir: "."` and `noUncheckedSideEffectImports: true`. Don't restate these defaults in tsconfig. Do list global types explicitly, e.g. `"types": ["node"]`. Source: https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/
- In Vite-bundled apps, use `"module": "preserve"` with `"moduleResolution": "bundler"`. Source: same.
- Don't use options deprecated in 6.0 and removed in 7.0: `baseUrl`, `moduleResolution: node`/`node10`/`classic`, `target: es5`, `downlevelIteration`, `module: amd`/`umd`/`systemjs`/`none`, `esModuleInterop: false`, `allowSyntheticDefaultImports: false`, `alwaysStrict: false`, the `module` keyword for namespaces, and `asserts` on imports (use `with`). Never set `ignoreDeprecations`. Why: this keeps the code ready for 7.0. Source: same.
- Use `paths` or subpath imports (`#...` in `package.json` `imports`) instead of `baseUrl` for aliases. Source: same.
- `lib: ["dom"]` now covers DOM iterables; don't add `dom.iterable`. Source: same.
- Don't pass file paths to `tsc` when a `tsconfig.json` is present; it's an error in 6.0. Source: same.

### Note on 7.0 (not adopted)
TypeScript 7.0 (the Go-native compiler, released 2026-07-08) has no programmatic API until 7.1. Tools that use the API, including typescript-eslint, svelte-check and the Svelte, Vue and Astro language tools, must stay on 6.0. Add a v7 delta once the toolchain supports it. Source: https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/

## SvelteKit (and Svelte 5) standards

### Base (researched at SvelteKit 3.1 / Svelte 5.57, 2026-10-16)

#### Project setup (SvelteKit 3)
- Configure SvelteKit through the `sveltekit({...})` plugin in `vite.config.js`. `svelte.config.js` is no longer supported, and `kit.*` options are now top-level. Minimum versions: Node 22.17, TypeScript 6, Svelte 5.57.1, Vite 8.0.12, vite-plugin-svelte 7. Source: https://svelte.dev/docs/kit/migrating-to-sveltekit-3
- Define the `#lib`/`#lib/*` subpath imports in `package.json` and import with file extensions (`#lib/foo.js`). `$lib` has been removed. Source: same.
- Extend `$app/tsconfig` in `tsconfig.json` with explicit `include`/`exclude`, not `.svelte-kit/tsconfig.json`. Source: same.
- Use `$app/state` (not the removed `$app/stores`), `$app/env` (not `$app/environment`), and `asset()`/`resolve()` from `$app/paths` (not `base`/`assets`/`resolveRoute`). Source: same.
- Navigation: use `goto(url, { shallow: true })` instead of `pushState`/`replaceState`, and `refreshAll` instead of `invalidateAll`. `goto` rejects external URLs; use `window.location.href` for those. Handle the `{ type: 'error' }` branch of `preloadData`. Source: same.
- Treat `page.url` as readonly; copy it before changing it. Source: same.
- Check errors with `isHttpError`/`isRedirect`, not `instanceof`. Use `Response.json()` and `new Response()`; `json()` and `text()` from the kit are deprecated. Source: same.
- Files or folders whose name contains a `server` segment are server-only. Source: same.

#### Static SPA mode
- For an SPA served by another backend, use `@sveltejs/adapter-static` with a `fallback` page, plus `export const ssr = false` in the root `+layout`. Prerender individual pages with `prerender = true; ssr = true` where possible. Don't name the fallback `index.html`, because it can conflict with prerendering. Don't use `+page.server.*`, `+layout.server.*` or `+server.*` files. Source: https://svelte.dev/docs/kit/single-page-apps
- Remote functions are still experimental. Don't use them in a static SPA. Source: https://svelte.dev/docs/kit/migrating-to-sveltekit-3

#### Svelte 5 components
- Always write new code in runes mode. Avoid the legacy features: `$:`, `export let`, `$$props`/`$$restProps`, `on:` directives, `<slot>`/`$$slots`/`<svelte:fragment>`, `<svelte:component>`, `<svelte:self>`, `use:` actions, the `class:` directive, and stores for shared state. Source: https://svelte.dev/docs/svelte/best-practices
- Use `$state` only for values that must trigger updates. Use `$state.raw` for large data that is replaced rather than mutated, such as API responses. Source: same.
- Compute values with `$derived`/`$derived.by` and side-effect-free expressions, not `$effect`. Values that depend on props must be `$derived`. Source: same.
- `$effect` is an escape hatch. Put user-triggered logic in event handlers, sync with external libraries via `{@attach}`, and use `<svelte:window>`/`<svelte:document>` for global listeners. Source: same.
- Events are attributes (`onclick={...}`). Use `{#snippet}`/`{@render}` for composition. Source: same.
- Share state through classes with `$state` fields, scoped with `createContext` instead of module-level state or `setContext`/`getContext`. Source: same.
- Key each `{#each}` block by a unique id, never the index. Use clsx-style `class` arrays or objects, and `style:--name={value}` for CSS variables. Source: same.

## Repo overrides

These rules apply to this repo and take precedence over the library sections above.

### core (`src/news/**`, `tests/**`, `alembic.ini`)
- Target Python 3.14 (`requires-python = ">=3.14"`) and manage dependencies and the venv with uv.
- Lint and format with ruff; type-check with pyright.
- Multi-exception `except` style is whatever `ruff format` (target py314) produces: `except A, B:` without `as`, `except (A, B) as error:` with it.
- Layering: `api/` and `cli/` may import `service/` but never each other, and `service/` imports neither. import-linter enforces this in `lint` (ADR 0017).
- Keep the database portable between SQLite and Postgres. Don't use SQLite-only or Postgres-only SQL features without a fallback, so use generic `JSON`, not `sqlite.JSONB` (ADR 0013). SQLite runs in WAL mode (ADR 0017).
- Scope every row by Reader, and by Channel where it belongs to one. Enforce this in the service layer, because the database doesn't (ADRs 0007, 0013).
- Logging: structlog, as JSON lines. The server process writes them to stdout; the CLI appends them to its log file (`--log-file` / `NEWS_CLI_LOG_FILE`, default `$XDG_STATE_HOME/news/cli.log`, else `~/.local/state/news/cli.log`), so CLI stdout carries only command output. Never log Secrets, LLM Provider keys, Gateway tokens or the Master Key, and never write them to disk (ADR 0009).
- Metrics: prometheus-client, exposed at `/metrics`.
- Credential storage (ADR 0009): use cryptography's AESGCM with 32-byte keys and fresh
  random 12-byte nonces at the storage edge. Authenticate the Reader id for wrapped Data
  Keys and the Reader/type/record id for credential values, so ciphertext swaps fail.
  Never include supplied key material in errors or logs. Reason: AES-GCM requires unique
  nonces per key and authenticates associated data alongside the ciphertext.
  Source: [cryptography 50.0.2 AESGCM documentation](https://cryptography.io/en/50.0.2/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM), accessed 2026-10-17.
- Serve the Web App with `app.frontend()`. The fallback filename must match `adapter-static`'s `fallback` (see the web section), e.g. `app.frontend("/", directory=<build dir>, fallback="200.html")`.
- LLM calls go only through the service layer's LLM Gateway, never directly to provider SDKs from Channel or Plugin code (ADRs 0008, 0012).
- Treat retrieved content (News Items, Source text, anything a Plugin fetched) as untrusted data in prompts: put it in clearly delimited data blocks, never concatenated into instruction text.
- Render Article text through an allowlist sanitizer before it reaches the Web App or Syndication Feed; never emit raw HTML produced by an LLM.

### web (`web/**`)
- Stay on TypeScript 6. SvelteKit 3.1, svelte-check 4.7 and typescript-eslint 8.71 don't support 7.0 yet (checked 2026-10-16).
- SvelteKit runs as a static SPA only: `adapter-static` with `fallback: '200.html'` and `ssr = false` in the root layout. No `+*.server.*` files and no remote functions. All server logic lives in FastAPI (ADR 0011).
- Use npm, ESLint (flat config) with Prettier, and Vitest for tests.
