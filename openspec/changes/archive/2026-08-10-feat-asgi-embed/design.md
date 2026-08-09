# Design: feat-asgi-embed

## Context

`create_asgi_app()` returns a `_ServingApp` whose `.asgi` is a plain Starlette app — embeddable in principle today. During construction, `ServerFetchPort.configure(asgi, blocked_paths, base_url=...)` binds the fetch port to that inner app (packages/webcompy-cli/src/webcompy_cli/_server.py). `configure_server_context(app, ...)` (packages/webcompy-server/src/webcompy_server/__init__.py) sets up server-side rendering including creating `app._server_fetch_port`. When WebComPy is mounted inside a host app, self-site fetches dispatched through the inner app can never reach host routes (e.g. the host's `/api/...`), because the inner Starlette instance has no knowledge of them.

## Goals / Non-Goals

**Goals:**
- Official, tested pattern: host ASGI app + `mount(prefix, serving.asgi)`.
- Self-site fetch from embedded components reaches the host's routes via `root_app` wiring.
- Clear `base_url` semantics under a mount prefix.

**Non-Goals:**
- SSG for embedded deployments; lifespan bridging; multi-embed guarantees.

## Decisions

### D1: Explicit `root_app` over implicit discovery
`configure_server_context(app, *, root_app=None)` — when `root_app` is provided, the CLI's default `fetch_port.configure(inner_asgi, ...)` is superseded: the fetch port binds to `root_app`. Self-site URLs resolve against the host's routing table.

**Why explicit**: there is no reliable way for the inner app to discover its host (ASGI has no back-reference). Alternatives considered: (b) absolute-URL fallback (fetch real network on 404 from inner app) — rejected: requires a listening socket even in-process, breaks SSG-style usage and tests, and silently changes semantics; (c) middleware that rewrites scope — fragile. Explicit wiring keeps responsibility visible at the embedding call site:

```python
serving = create_asgi_app(app, build_config)
configure_server_context(app, root_app=host)  # fetch port targets the host
host.mount("/admin", serving.asgi)
```

### D2: `base_url` must equal the mount prefix
With `host.mount("/admin", ...)`, WebComPy's internal routes live under `/admin`. Setting `AppConfig.base_url="/admin/"` makes asset URLs, router links, and self-site URL resolution (`base_url`-relative resolution per `server-fetch-asgi`) align with the embedded location. The spec requires this pairing and the docs show it; a mismatch produces broken asset URLs, which is detectable in verification tests.

Synergy note: `HistoryPort` now owns browser URL updates (`push_url`/`replace_url`, `port-abstraction` spec) and builds browser-visible URLs from `base_url`. With the pairing above, client-side navigation and guard-driven redirects inside the embedded app automatically produce correctly prefixed history URLs with no embed-specific code.

### D3: Blocked paths are prefixed, not widened
Page-route blocking prevents SSR fetches from recursing into HTML page routes. Under embedding, the blocked set is WebComPy's page paths prefixed by the mount prefix (e.g. `/admin/users`), because that is where the host actually serves them. Host API routes (e.g. `/api/...`) are NOT blocked — they are the intended fetch targets.

### D4: Server-driven verification matrix
Tests and an example cover: (1) SSR page render through the host mount; (2) `/_webcompy-*` asset endpoints under the prefix; (3) self-site fetch to a host API endpoint during SSR with response baked into hydration payload; (4) direct request to the host API unaffected. `run_server()` is not used in embedded mode (the host owns uvicorn); docs state that `create_asgi_app` + manual wiring replaces `run_server`.

### D5: The `/_webcompy-resource` route is base_url-prefixed — embedding must compensate
Unlike every other framework route, the resource route is registered INSIDE the serving app with the `base_url` prefix baked in (`base_url_stripped + "/_webcompy-resource/{path:path}"` in `_server.py`), and the browser-side URL builder (`ports/_browser/_resource.py`) likewise prefixes `base_url`; the `cli` spec describes the endpoint as `GET {base_url}_webcompy-resource/{path:path}`. In standalone mode the request path arrives already prefixed, so this matches. Under embedding, Starlette's `Mount` strips the mount prefix before the inner app sees the request; with the required `base_url` == mount-prefix pairing (D2), the inner route would then carry a DOUBLE prefix and never match, breaking resource loading. The implementation SHALL adjust resource-route construction in embedded mode (e.g. register the route without the `base_url` prefix when `root_app` is configured) and SHALL keep standalone behavior byte-identical. Because standalone behavior is unchanged, no `cli` spec delta is required; the `asgi-embed` spec carries the embedded-mode requirement.

## Risks / Trade-offs

- [Double-dispatch cost: self-site fetches re-enter the host app and route back into WebComPy for page paths] → Only when components fetch page paths, which blocked_paths already prevents; API fetches terminate at host endpoints.
- [`configure()` currently raises when called twice — CLI internally calls it once with the inner app] → The embedding path must bypass/replace that call; implementation adds an explicit reconfiguration path (e.g. `configure(..., allow_rebind=True)` or deferring the CLI call when `root_app` is set). Detail finalized in implementation; spec constrains behavior, not mechanism.
- [`configure_server_context` re-instantiates the fetch port] → `configure_server_context()` assigns a fresh `ServerFetchPort` to `app._server_fetch_port` on every call. The documented embedding order (`configure_server_context(app, root_app=host)` AFTER `create_asgi_app()`) relies on this: the second call replaces the CLI-configured port, and render contexts read `app._server_fetch_port` at context creation, so subsequent requests use the root-bound port. The `root_app` binding must re-derive prefixed blocked paths and `base_url` for the replacement port. The order is also mandatory: `create_asgi_app()` internally calls `configure_server_context()` via `resolve_build_artifacts`, so a call BEFORE it would be overwritten.
- [Host middleware (auth, CORS) now wraps WebComPy responses] → Generally desirable; documented as a feature of embedding.
- [Hash-mode embedding] → Supported identically (pre-rendered shell served under the prefix); covered by a test.

## Migration Plan

None. Default behavior (`root_app=None`) is byte-identical to today.

## Open Questions

- Exact mechanism for superseding the CLI's `configure()` call (rebind flag vs. deferral) — implementation detail to settle with tests.
