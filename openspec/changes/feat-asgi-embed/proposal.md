# Proposal: feat-asgi-embed

## Why

Teams with an existing FastAPI (or other ASGI) application often want to add a small admin UI or internal tool without standing up a separate frontend stack. WebComPy's serving app is already a plain ASGI callable, so embedding should be possible — and it nearly works today via `outer.mount("/admin", serving.asgi)`. But there is one structural blocker: `ServerFetchPort.configure()` is bound to the inner WebComPy ASGI app, so self-site fetches from embedded components can only reach WebComPy's own routes — they cannot reach the outer app's endpoints (the very APIs an embedded admin UI exists to consume). This change makes embedding an officially supported, documented pattern with the wiring to make self-site fetch reach the outer application.

## What Changes

- `configure_server_context()` gains an optional `root_app` parameter: when provided, `ServerFetchPort` is configured against the outer (root) ASGI application instead of WebComPy's internal serving app, so self-site fetches traverse the full outer routing table (sibling mounts, outer API routes).
- Official embedding pattern documented: build the serving app via `create_asgi_app()`, mount `serving.asgi` under a path prefix in the host app, and pass the host app as `root_app`.
- `AppConfig.base_url` SHALL be set to the mount prefix so generated URLs (assets, page links, self-site fetch resolution) align with the embedded location; the spec defines how `base_url` interacts with the mount prefix.
- Blocked-path semantics adapt: when `root_app` is used, page-route blocking is evaluated against WebComPy's page paths under the mount prefix; outer API routes remain fetchable.
- Verified support matrix: SSR rendering embedded under a host FastAPI app; static/asset endpoints served correctly under the prefix; self-site fetch reaching outer endpoints during SSR.
- Out of scope: running under SSG (embedding is a server-runtime pattern), hot reload inside a host app.

## Capabilities

### New Capabilities

- `asgi-embed`: Embedding a WebComPy serving app into a host ASGI application, including fetch-port wiring (`root_app`), `base_url`/prefix alignment, and blocked-path behavior.

### Modified Capabilities

- `server-fetch-asgi`: `ServerFetchPort.configure()` SHALL support binding to a root ASGI app distinct from WebComPy's internal serving app, with self-site resolution and blocking evaluated accordingly.

## Impact

- **Code**: `packages/webcompy-server/src/webcompy_server/__init__.py` (`configure_server_context` signature), `packages/webcompy-server/src/webcompy_server/ports/_fetch.py` (root-app binding), docs and an example project.
- **APIs**: additive parameter; no breaking changes.
- **Dependencies**: none.
- **Specs**: new `asgi-embed`; delta to `server-fetch-asgi`.

## Known Issues Addressed

(none)

## Non-goals

- Mounting external apps INTO WebComPy (that is `feat-asgi-mount`).
- An embedded app that simultaneously configures its own `WebComPyServerConfig.mounts` (combining `root_app` binding with inner mounts) — unspecified; may be addressed by a future change.
- Lifespan bridging beyond what Starlette mounting already provides (host app owns startup/shutdown; WebComPy has no server-side lifespan needs today).
- Multiple embedded WebComPy apps in one host (not verified; may work, not guaranteed).
- SSG for embedded deployments.
