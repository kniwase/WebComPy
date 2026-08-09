# Proposal: feat-asgi-mount

## Why

WebComPy's server currently exposes only framework-owned endpoints (`/_webcompy-*`, static files, and the SSR catch-all). There is no way for a project to attach its own HTTP endpoints. Python's natural home is the server side, and users who want "a small app with a backend" — a REST API for the frontend, a webhook receiver, an admin data endpoint — must run a separate server process today. The `server-fetch-asgi` spec already assumes components can fetch "their own application's API endpoints" during SSR/SSG, but provides no way to create such endpoints. Allowing users to mount arbitrary ASGI applications (e.g. FastAPI) into the WebComPy server closes this gap with minimal framework surface.

## What Changes

- `WebComPyServerConfig` gains a `mounts` field: a zero-argument callable returning `dict[str, ASGIApp]` (path prefix → ASGI app). The callable form defers import/construction of user apps until server startup.
- `create_asgi_app()` inserts one Starlette `Mount` per entry BEFORE the SSR catch-all route (`/{path:path}`), so mounted apps take precedence over page rendering.
- Mount path prefixes that collide with a framework-reserved prefix (`/_webcompy-*`) or with a registered page route SHALL cause a startup error listing the conflicting paths.
- Self-site fetches to mounted paths during SSR/SSG work through the existing `ServerFetchPort` ASGITransport path; fetched responses are collected into the hydration transfer cache as today (bake-on-SSG behavior is unchanged). Mount prefixes SHALL be excluded from `blocked_paths` semantics (they are intended fetch targets, not page routes). Mount prefixes SHALL also be excluded from `base_url` prefixing in self-site URL resolution (mounts are absolute server paths), so mounted endpoints are reachable via self-site fetch under any `base_url`.
- SSG (`webcompy generate`) SHALL work unchanged when mounts are configured: only page routes are written to `dist/`; mounts are reachable in-process during generation for data fetching.
- Hash-mode: mounts are mounted identically; since hash-mode pages are pre-rendered at startup, mounted endpoints behave the same as in history mode.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cli`: The server route table gains user-provided ASGI mounts, inserted before the SSR catch-all; collision detection with reserved prefixes and page routes is required.
- `server-fetch-asgi`: Mount path prefixes SHALL NOT be treated as blocked page paths; self-site fetches to mounts SHALL resolve through the ASGI transport. The base_url-resolution requirement is MODIFIED: paths under a mount prefix are exempt from `base_url` prefixing (mounts are absolute server paths).
- `ssg-via-ssr`: SSG SHALL remain functional when mounts are configured; mount endpoints SHALL be reachable via ASGITransport during generation; mount responses SHALL NOT be written into `dist/`.
- `project-config`: `WebComPyServerConfig` gains the `mounts` field.

## Impact

- **Code**: `packages/webcompy-cli/src/webcompy_cli/config/_server_config.py` (new field), `packages/webcompy-cli/src/webcompy_cli/_server.py` (route assembly + collision detection + passing mount prefixes to the fetch port), `packages/webcompy-server/src/webcompy_server/ports/_fetch.py` (base_url-prefix exemption for mount paths), possibly `packages/webcompy-cli/src/webcompy_cli/_generate.py` (no change expected; verification only).
- **APIs**: `WebComPyServerConfig(mounts=...)` (additive, backward compatible).
- **Dependencies**: None (Starlette `Mount` is already available).
- **Specs**: `openspec/specs/cli/spec.md`, `server-fetch-asgi`, `ssg-via-ssr`, `project-config`.

## Known Issues Addressed

(none)

## Non-goals

- Typed clients or RPC on top of mounted apps (separate changes: `feat-typed-api-client`, `feat-json-rpc`).
- Mounting WebComPy itself into an external ASGI app (separate change: `feat-asgi-embed`).
- Middleware configuration for mounted apps (users configure middleware inside their own app).
- Per-mount SSG export (mounts are runtime endpoints; only their responses fetched during page rendering are baked into hydration payloads via the existing transfer cache).
