## Why

During server-side rendering (SSR) and static site generation (SSG), components may need to fetch data from API endpoints defined within the same application. Currently, `ServerFetchPort` uses a plain `httpx.AsyncClient()` for all requests, which means:

1. **Self-site requests go through the network stack** — A request to `/api/data` during SSG requires the dev server to be running and accessible over HTTP, which is fragile and slow.
2. **No recursion protection** — If a page component fetches its own page URL during SSR, it triggers an infinite recursion that hangs the process.
3. **No URL classification** — All URLs are treated identically; there is no concept of "self-site" vs. "external".

This change adds self-site fetch support to `ServerFetchPort` using `httpx.ASGITransport`, so that same-application requests are routed through the app's own ASGI app internally, without network I/O. It also adds page-route blocking to prevent infinite recursion during SSR/SSG.

This change depends on `feat/async-rendering-pipeline` because `ServerFetchPort.fetch()` is an async method that can only be called during the async `_render` phase.

## What Changes

- **`packages/webcompy/src/webcompy/ports/_fetch.py`** — Add `is_self_site_url(url)` method to `FetchPort` ABC for URL classification.
- **`packages/webcompy-server/src/webcompy_server/ports/_fetch.py`** — Major changes to `ServerFetchPort`:
  - Add `configure(asgi_app, blocked_paths)` method for lazy initialization after ASGI app creation.
  - Add self-site URL detection: URLs starting with `/` or `.` are treated as self-site.
  - Route self-site requests through `httpx.ASGITransport` wrapping the app's ASGI app.
  - Return 500 for blocked paths (page routes that return HTML) to prevent infinite recursion.
  - Keep external URL handling via normal `httpx.AsyncClient`.
  - Add `close()` cleanup for both clients.
- **`packages/webcompy/src/webcompy/app/_app.py`** — Retrieve `ServerFetchPort` from DI scope after initialization for later configuration.
- **`packages/webcompy-cli/src/webcompy_cli/_server.py`** — Call `ServerFetchPort.configure(asgi_app, blocked_paths)` after ASGI app creation.
- **`packages/webcompy-cli/src/webcompy_cli/_generate.py`** — Call `ServerFetchPort.configure(asgi_app, blocked_paths)` during SSG with a temporary ASGI app.

## Capabilities

### New Capabilities
- `server-fetch-asgi`: Self-site fetch during SSR/SSG, routing requests through the app's own ASGI app via `httpx.ASGITransport`, with page-route blocking to prevent infinite recursion.

### Modified Capabilities
- `port-abstraction`: `FetchPort` ABC gains `is_self_site_url()` method.

## Dependencies

- **Requires** `feat/async-rendering-pipeline` — `ServerFetchPort.fetch()` is an async method that can only be called during the async `_render` phase.

## Impact

- `packages/webcompy/src/webcompy/ports/_fetch.py` — ABC change (new method).
- `packages/webcompy-server/src/webcompy_server/ports/_fetch.py` — Major rewrite of `ServerFetchPort`.
- `packages/webcompy/src/webcompy/app/_app.py` — Minor change to expose `ServerFetchPort` reference.
- `packages/webcompy-cli/src/webcompy_cli/_server.py` — Add configuration call after ASGI app creation.
- `packages/webcompy-cli/src/webcompy_cli/_generate.py` — Add ASGI app creation and `ServerFetchPort` configuration for SSG.
- No browser-side changes.
- No breaking changes to existing external-fetch behavior.

## Known Issues Addressed

- No specific known issue tracked in `openspec/config.yaml`. This is a new capability enabling SSR data fetching.

## Non-goals

- Changing the `BrowserFetchPort` API or behavior (browser fetch already works correctly).
- Adding caching or deduplication for self-site requests.
- Supporting WebSocket connections through ASGI transport.
- Modifying the `HttpClient` composable (it already delegates to `FetchPort`).
- Adding request timeout configuration (httpx defaults are sufficient).