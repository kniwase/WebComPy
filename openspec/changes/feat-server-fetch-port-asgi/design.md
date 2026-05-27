## Context

WebComPy components may need to fetch data during SSR/SSG. For example, a page component might call `FetchPort.fetch("/api/users")` during rendering. Currently, `ServerFetchPort` uses a plain `httpx.AsyncClient()` for all requests, which requires the dev server to be running and accessible over HTTP for self-site requests. This is fragile (network-dependent), slow (round-trip through the network stack), and dangerous (no recursion protection).

This change introduces self-site fetch: requests to URLs within the same application are routed through `httpx.ASGITransport`, which wraps the app's own ASGI app. This eliminates network I/O for self-site requests and enables SSG-time data fetching without a running server.

## Goals / Non-Goals

**Goals:**
- Enable components to fetch data from their own application's API endpoints during SSR/SSG
- Route self-site requests through the ASGI app directly (no network hop)
- Prevent infinite recursion when a page component fetches its own page URL
- Support URL classification (self-site vs. external)
- Lazy configuration to solve the chicken-and-egg problem (ServerFetchPort created before ASGI app)

**Non-Goals:**
- Changing BrowserFetchPort behavior
- Request caching or deduplication
- WebSocket support through ASGI transport
- Modifying HttpClient composable
- Adding request timeout configuration

## Decisions

### Decision: URL classification via path prefix

URLs are classified as self-site if they start with `/` (absolute path) or `.` (relative path). All other URLs (starting with `http://`, `https://`, etc.) are external.

**Rationale:** This is the simplest classification that matches how developers typically write self-site fetch calls in components. Absolute paths like `/api/data` are the most common pattern. Relative paths like `./data` are less common but should also work.

**Alternatives considered:**
- Check against `base_url` config: More accurate but requires access to config at fetch time and adds complexity for resolving relative URLs.
- Accept a list of allowed origins: Over-engineered for the current use case.

### Decision: Lazy configuration via `configure()` method

`ServerFetchPort` is created in `WebComPyApp.__init__()` but the ASGI app doesn't exist yet. Instead of restructuring the initialization order, we add a `configure(asgi_app, blocked_paths)` method that is called after the ASGI app is created.

**Rationale:** This is the minimal change that solves the chicken-and-egg problem. The `ServerFetchPort` is functional (for external requests) immediately after construction. Self-site requests fail with a clear error if `configure()` hasn't been called yet.

**Alternatives considered:**
- Pass ASGI app to `WebComPyApp.__init__()`: Would require restructuring the app creation flow and exposing internal ASGI details to the user.
- Use a factory pattern: Over-engineered; lazy configuration is simpler.
- Use a module-level global: Breaks multi-app isolation.

### Decision: Page-route blocking returns HTTP 500

When a self-site fetch request targets a path that is a page route (i.e., one that returns HTML), the `ServerFetchPort` returns a `Response` with status 500 instead of making the request. This prevents infinite recursion where a page component fetches its own URL during SSR.

**Rationale:** A 500 response clearly indicates a programming error (fetching your own page during rendering). It's not a 404 (the route exists) or a redirect (which could still cause loops).

**Alternatives considered:**
- Raise an exception: Would crash the entire SSR process; returning 500 lets the component handle it gracefully.
- Return 429 (rate limit): Semantically incorrect; this is a logical error, not a rate limit.
- Return 403 (forbidden): Misleading; the route is accessible, just not during SSR.
- Return empty response: Silently failing makes debugging harder.

### Decision: Two httpx clients (self-site and external)

`ServerFetchPort` maintains two httpx clients:
1. `_external_client`: `httpx.AsyncClient()` for external URLs (always present).
2. `_self_site_client`: `httpx.AsyncClient(transport=httpx.ASGITransport(app=asgi_app))` for self-site URLs (created by `configure()`).

**Rationale:** `httpx.ASGITransport` wraps an ASGI app and routes requests internally. Using separate clients keeps the code clear and avoids transport configuration leaking between request types.

### Decision: `base_url` is prepended for self-site path resolution

When `base_url` is set (e.g., `/myapp/`), self-site absolute paths are resolved relative to `base_url`. For example, with `base_url="/myapp/"`, a fetch to `/api/data` resolves to `/myapp/api/data`.

**Rationale:** This matches how the dev server and SSG handle base URLs — all routes are mounted under `base_url`.

## Risks / Trade-offs

- **[Risk]** Self-site requests bypass middleware stack — `httpx.ASGITransport` calls the ASGI app directly, so any middleware that depends on actual HTTP connections (e.g., rate limiting by IP) won't work. → **Mitigation:** This is expected and documented. Self-site requests are internal application calls, not user-facing HTTP requests.
- **[Risk]** `configure()` must be called before any self-site fetch — If a component fetches a self-site URL before `configure()` is called, the request fails. → **Mitigation:** `configure()` is called immediately after ASGI app creation in both `create_asgi_app()` and `generate_static_site()`. This happens before any rendering. In the unlikely case it's not called, a clear error message is returned.
- **[Risk]** Blocked paths must be determined at configuration time — If new routes are added dynamically, blocked paths may be stale. → **Mitigation:** Routes are defined at app creation time and don't change during SSR/SSG, so this is not a practical concern.
- **[Risk]** httpx version compatibility with ASGITransport — `httpx.ASGITransport` was introduced in httpx 0.23+. → **Mitigation:** WebComPy already depends on httpx (used by `ServerFetchPort`), so the version requirement is already met.

## Implementation Outline

1. Add `is_self_site_url()` to `FetchPort` ABC.
2. Add `configure()` method and dual-client logic to `ServerFetchPort`.
3. Determine blocked paths from `app.routes` in `_server.py` and `_generate.py`.
4. Call `configure()` after ASGI app creation in both server and SSG paths.
5. Handle `base_url` prefix for self-site URL resolution.
6. Add unit tests for URL classification, self-site routing, and blocking.

## Open Questions

1. Should relative URLs like `./data` be resolved against the current route path? (Current decision: resolve against `base_url` root, not current path — simpler and more predictable.)
2. Should blocked paths be configurable by the developer? (Current decision: no, they are derived from `app.routes` automatically.)