# Design: feat-asgi-mount

## Context

`create_asgi_app()` (packages/webcompy-cli/src/webcompy_cli/_server.py) builds a flat list of Starlette `Route` objects: internal `/_webcompy-*` endpoints, one route per static file, and a final `/{path:path}` catch-all that performs SSR. The route list is assembled locally with no extension point. `WebComPyServerConfig` (packages/webcompy-cli/src/webcompy_cli/config/_server_config.py) currently holds only `port` and `dev`. SSG (`generate_static_site`) fetches pages through the same ASGI app via `httpx.ASGITransport`, and `ServerFetchPort` routes self-site fetches through the same transport with `blocked_paths` derived from page routes.

## Goals / Non-Goals

**Goals:**
- Let projects mount arbitrary ASGI apps (FastAPI, Starlette, raw ASGI callables) at chosen path prefixes.
- Zero interference with SSR/SSG and framework endpoints; explicit error on path collisions.
- Self-site fetch to mounts works in-process during SSR and SSG with no extra wiring.

**Non-Goals:**
- Mounting WebComPy into an external app (see `feat-asgi-embed`).
- Middleware/auth configuration on behalf of mounted apps.
- Any typed client or RPC layer.

## Decisions

### D1: Declaration via `WebComPyServerConfig.mounts` as a lazy callable
```python
@dataclass
class WebComPyServerConfig:
    port: int = 8080
    dev: bool = False
    mounts: Callable[[], dict[str, ASGIApp]] | None = None
```
Usage:
```python
def mounts():
    from my_app.api import api  # FastAPI app; imported lazily
    return {"/api": api}

config = WebComPyBuildConfig(..., server=WebComPyServerConfig(mounts=mounts))
```
**Why a callable**: importing a FastAPI app at config-import time would drag server-only dependencies into any context that imports the config (including tooling and resolution logic) and slow CLI startup. The callable is invoked exactly once inside `create_asgi_app()`. Alternatives considered: (a) a plain `dict` field — rejected (import-time side effects); (b) a separate config file — rejected (project-config deliberately consolidated to a single `webcompy_config.py`).

### D2: Insert `Mount` entries before the HTML catch-all
Starlette matches routes in order; `/{path:path}` swallows everything. Mounts are inserted after all `/_webcompy-*` and static-file routes, immediately before the catch-all page route. Within a mount, the user's app owns routing entirely.

**Why**: minimal reordering; existing behavior for all current routes is unchanged.

### D3: Collision detection at startup
Before building the app, validate mount prefixes:
- MUST NOT start with `/_webcompy` (framework-reserved).
- MUST NOT equal or prefix-collide with a registered page route pattern (compare against `app.routes` paths; static path params complicate exact matching, so the check treats a mount prefix as colliding when a page route's static prefix is identical to or under the mount prefix).
- On collision: raise `WebComPyException` listing all conflicts at server startup / SSG start (fail fast).

**Why**: silent shadowing (either a page swallowing `/api/...` or a mount hiding a page) would be extremely confusing. A startup error is the only sane behavior.

### D4: FetchPort gains mount awareness for base_url resolution
`ServerFetchPort.configure(asgi, blocked_paths, base_url=..., mount_prefixes=...)` is already called with the fully assembled app — including mounts — because `configure()` runs after `Starlette(routes=...)` construction; this change adds the configured mount prefixes to the call. `blocked_paths` derives from page routes only, so mount paths are not blocked by construction. One code change to the fetch port IS required: self-site URL resolution exempts mount paths from `base_url` prefixing. Mounts are absolute server paths (the route table does NOT prefix them by `base_url`, per the `cli` delta), so a fetch to `/api/users` under `base_url="/myapp"` must be dispatched as `/api/users` — not `/myapp/api/users` — to reach the mount. Without the exemption, mounted endpoints are unreachable via self-site fetch under any non-root `base_url`. The `server-fetch-asgi` base_url-resolution requirement is MODIFIED accordingly.

### D5: SSG is mount-aware but mount-silent
`generate_static_site` only GETs page routes and `/_webcompy_404`, so mounts never leak into `dist/`. Components that fetch mount endpoints during SSG get responses via ASGITransport, cached into the hydration transfer payload as with any self-site fetch. Deployed static sites then replay those responses without a server (existing hydration behavior).

**Trade-off accepted**: a static deployment has no live `/api`; data fetched at build time is baked, and runtime-only fetches against mounts will fail on static hosting. This is inherent to SSG and documented; per-call opt-out of baking is handled in `feat-typed-api-client` (`transfer=False`).

## Risks / Trade-offs

- [Mount paths vs `base_url`] → Mount paths are absolute server paths, independent of `app.base_url`. Self-site fetch resolution exempts mount paths from `base_url` prefixing (D4), so mounted endpoints are reachable under any `base_url`. Docs still note that mounts are NOT prefixed by `base_url` in the route table (unlike page routes), with a spec scenario + example showing fetch URL vs mount path under a non-root `base_url`.
- [Callable returning a fresh app each call] → `create_asgi_app()` invokes the callable once and caches the result on the serving app; document single-invocation semantics.
- [Lifespan events of mounted apps (FastAPI startup/shutdown)] → Starlette `Mount` propagates lifespan only if the parent app is served with lifespan support; `run_server` uses `uvicorn.run(serving.asgi)` which handles Starlette lifespan. Document that mounted-app lifespan works via Starlette's router lifespan; edge cases deferred.
- [Mounted apps share the process and event loop with SSR] → A blocking mounted endpoint blocks page rendering. Document that mounted apps should be async; no enforcement.

## Migration Plan

None. `mounts=None` default preserves current behavior exactly.

## Open Questions

- Exact collision-detection semantics for parameterized page routes (`/users/{id}` vs mount `/users`): proposal — treat as collision only when the page route's literal prefix is under the mount prefix; finalize during implementation with tests.
