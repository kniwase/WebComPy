# Proposal: SSG via SSR

## Why

The current SSG pipeline (`generate_static_site()` in `_generate.py`) and the dev server (`create_asgi_app()` in `_server.py`) duplicate significant amounts of setup logic: dependency resolution, lockfile handling, wheel building, WASM/runtime asset management, and `html_generator` construction. Additionally, `generate_static_site()` calls `html_generator()` (a synchronous partial of `generate_html()`) directly, bypassing the full ASGI request lifecycle. This means SSG cannot exercise route matching, the DI scope per-request pattern, or the async rendering pipeline — making SSG output diverge from what the dev server actually serves.

The upcoming `feat/async-rendering-pipeline` change makes `generate_html()` return an `Awaitable[str]` instead of `str`, which breaks the synchronous SSG pipeline entirely. The `feat/server-fetch-port-asgi` change adds ASGI-based fetch support that also requires async SSR. Rather than maintaining two separate code paths, we restructure SSG to reuse the ASGI app via `httpx.AsyncClient(transport=ASGITransport(app=asgi_app))`, eliminating duplication and ensuring SSG output matches dev server output exactly.

## What Changes

- **RESTRUCTURE** `generate_static_site()` — becomes async, creates an ASGI app via `create_asgi_app()`, then fetches each route via `httpx.AsyncClient(transport=ASGITransport(app=asgi_app))`
- **EXTRACT** shared setup logic — `_resolve_build_artifacts()` from duplicated code in `_generate.py` and `_server.py` into a common function that returns all resolved build artifacts (wheels, lockfile data, URLs, etc.)
- **MAKE** `send_html()` async — the SSR handler in `_server.py` awaits `html_generator()` instead of calling it synchronously
- **MAKE** `generate_html()` async — returns `Awaitable[str]` (required by `feat/async-rendering-pipeline`)
- **ADD** SSG-specific ASGI app mode — `create_asgi_app()` accepts a flag or mode parameter to exclude dev-only features (SSE reload endpoint)
- **ADD** blocked-path handling for SSR — page routes return 500 when fetched via `ServerFetchPort` to prevent infinite recursion (provided by `feat/server-fetch-port-asgi`)
- **UPDATE** hash mode SSR — pre-renders once with async `html_generator()` and serves the cached result

## Capabilities

### New Capabilities

- `ssg-via-ssr`: SSG reuses the ASGI app to generate static HTML for each route, ensuring parity between dev server output and SSG output. The `generate_static_site()` function creates a minimal ASGI app, fetches each route via ASGITransport, and writes the response HTML to disk.

## Known Issues Addressed

- **SSG and dev server code duplication** — shared setup logic extracted into `_resolve_build_artifacts()`; both `_generate.py` and `_server.py` call it
- **SSG output divergence from dev server** — SSG now uses the same ASGI pipeline, so output is identical
- **Synchronous `generate_html()` blocks async rendering** — `generate_html()` becomes async, enabling the rendering pipeline to await async operations (fetch, effects)

## Non-goals

- Changing the public API of `generate_static_site()` or `create_asgi_app()` (beyond adding an optional mode parameter)
- Modifying how the dev server handles live reload (SSE endpoint remains dev-only)
- Replacing `httpx` with a different HTTP client
- Changing the lockfile or wheel builder logic
- Adding incremental or partial SSG (only full-site generation is supported)
- Making `WebComPyApp.run()` async (browser-side code remains synchronous)

## Dependencies

- **Requires** `feat/async-rendering-pipeline` — `generate_html()` must return `Awaitable[str]`
- **Requires** `feat/server-fetch-port-asgi` — `ServerFetchPort` must use the ASGI app for fetch requests, and blocked-path handling prevents infinite recursion during SSR

## Impact

- **Affected modules**: `webcompy/cli/_generate.py` (major restructure), `webcompy/cli/_server.py` (async SSR handler, shared setup extraction), `webcompy/cli/_html.py` (async `generate_html()`), `webcompy/app/_app.py` (integration with async rendering)
- **Affected specs**: `cli`, `architecture`, `app-lifecycle`, `app-config`
- **Breaking**: `generate_html()` signature changes from sync to async — internal API, not public
- **Testing**: Existing SSG tests should pass unchanged (output is identical); new unit tests for `_resolve_build_artifacts()` and async SSR pipeline