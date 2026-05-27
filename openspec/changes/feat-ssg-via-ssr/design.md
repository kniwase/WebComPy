# Design: SSG via SSR

## Context

WebComPy has two server-side code paths that produce HTML:

1. **Dev server** (`_server.py`): Creates a Starlette ASGI app with routes for wheel files, static files, WASM assets, runtime assets, SSE reload, and an HTML catch-all route. Each request enters `app.di_scope`, sets the path, and calls `html_generator()`.

2. **SSG pipeline** (`_generate.py`): `generate_static_site()` resolves dependencies, builds wheels, downloads assets, creates an `html_generator` partial, then iterates routes and writes HTML files directly.

Both paths share ~60% of their code: dependency resolution, lockfile handling, WASM/runtime asset management, and wheel building. The SSG path duplicates this logic rather than reusing the ASGI app.

The `feat/async-rendering-pipeline` change makes `generate_html()` return `Awaitable[str]`, which breaks the synchronous call `html_generator()` in both files. The `feat/server-fetch-port-asgi` change makes `ServerFetchPort` use the ASGI app itself for fetch requests, requiring async SSR. Rather than patching both code paths independently, this change unifies them.

## Goals / Non-Goals

**Goals:**
- Restructure SSG to create an ASGI app and fetch routes via `httpx.AsyncClient(transport=ASGITransport(app=asgi_app))`
- Make `send_html()` and `generate_html()` async
- Extract shared setup logic into `_resolve_build_artifacts()` to eliminate duplication
- Support both dev mode and SSG mode in `create_asgi_app()`
- Maintain identical HTML output between dev server and SSG

**Non-Goals:**
- Incremental or partial SSG
- Changing the public CLI interface
- Modifying the dev server's SSE reload behavior
- Replacing httpx

## Decisions

### Decision 1: SSG = SSR + ASGITransport

**Chosen**: `generate_static_site()` creates an ASGI app via `create_asgi_app()` (with SSG mode), then uses `httpx.AsyncClient(transport=ASGITransport(app=asgi_app))` to fetch each route and write the response HTML to disk.

**Key ordering constraint**: `ServerFetchPort.configure()` MUST be called after `create_asgi_app()` returns and BEFORE any route is fetched. This ensures self-site fetch requests during SSR are routed through the ASGI app. The call site is immediately after `create_asgi_app()` and before the `httpx.AsyncClient` context manager block.

```python
async def generate_static_site(app: WebComPyApp | None = None):
    # ... resolve build_config ...
    asgi_app = create_asgi_app(app, build_config, mode="ssg")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),
        base_url="http://test",
    ) as client:
        if app.router_mode == "history" and app.routes:
            for path, _, _, _, page in app.routes:
                paths = (
                    {path.format(**params) for params in path_params}
                    if (path_params := page.get("path_params"))
                    else {path}
                )
                for route_path in paths:
                    response = await client.get(f"/{app.config.base_url.strip('/')}/{route_path}")
                    html = response.text
                    # ... write html to dist_dir / route_path / index.html ...
            # 404 page
            response = await client.get(f"/{app.config.base_url.strip('/')}///:404://")
            # ... write 404.html ...
        else:
            response = await client.get(f"/{app.config.base_url.strip('/')}/")
            # ... write index.html ...
```

**Rationale**: Using ASGITransport means SSG exercises the exact same code path as the dev server: route matching, DI scope entry, path setting, and HTML generation. This eliminates output divergence. The `base_url` is included in the URL so that `base_url_stripper` in the handler processes correctly.

**Trade-offs**: ASGITransport adds httpx as a runtime dependency for SSG, but httpx is already a dependency (used by `ServerFetchPort`). The overhead of creating an ASGI app and making HTTP requests is minimal compared to wheel building and dependency resolution.

### Decision 2: generate_html() becomes async

**Chosen**: `generate_html()` changes from `def generate_html(...)` returning `str` to `async def generate_html(...)` returning `Awaitable[str]`. Callers must `await` the result.

```python
async def generate_html(
    app: WebComPyApp,
    app_package_name: str,
    dev_mode: bool,
    prerender: bool,
    app_version: str,
    wheel_filename: str,
    ...
) -> str:
    # ... existing HTML generation logic ...
    # Async rendering pipeline: await any async effects
    html = _HtmlElement(...).render_html()
    return "<!doctype html>" + html.replace("</body>", f"{app_loader_html}</body>")
```

**Rationale**: The `feat/async-rendering-pipeline` change requires `generate_html()` to be async so that the rendering pipeline can await async effects (e.g., `ServerFetchPort.fetch()` during SSR). The function signature remains the same except for the `async` keyword.

**Impact**: All callers of `generate_html()` must be updated:
- `_server.py`: `send_html()` awaits `html_generator()`
- `_generate.py`: eliminated (SSG uses ASGITransport instead)
- Tests: any direct calls must `await`

### Decision 3: send_html() becomes async

**Chosen**: The `send_html()` route handler in `_server.py` becomes `async def send_html()` and awaits `html_generator()`.

```python
async def send_html(request: Request):
    with app.di_scope:
        path: str = request.path_params.get("path", "")
        requested_path = base_url_stripper(path).strip("/")
        accept_types: list[str] = request.headers.get("accept", "").split(",")
        routes = r if (r := app.routes) else []
        is_matched = truth(tuple(filter(lambda r: r[1](requested_path, routes)))
        if is_matched or "text/html" in accept_types:
            app.set_path(requested_path)
            html = await html_generator()
            return HTMLResponse(html)
        else:
            raise HTTPException(404)
```

For hash mode (pre-rendered once at startup):

```python
# Pre-render at startup
with app.di_scope:
    app.set_path("/")
    html = await html_generator()

async def send_html(_: Request):
    return HTMLResponse(html)
```

**Rationale**: Since `generate_html()` is now async, the handler must await it. For hash mode, pre-rendering at startup also needs to await.

### Decision 4: Shared setup logic — _resolve_build_artifacts()

**Chosen**: Extract the duplicated dependency resolution, lockfile handling, WASM/runtime asset management, and wheel building logic into `_resolve_build_artifacts()` in a new module `webcompy/cli/_build.py`. Both `_generate.py` and `_server.py` call this function.

```python
@dataclass
class BuildArtifacts:
    app_version: str
    wheel_filename: str
    extra_wheel_filenames: list[str] | None
    pyodide_package_names: list[str]
    wasm_local_urls: dict[str, str] | None
    lockfile_url: str | None
    runtime_serving: str
    # For dev server: in-memory file maps
    app_package_files: dict[str, tuple[bytes, str]] | None
    wasm_asset_files: dict[str, pathlib.Path] | None
    runtime_asset_files: dict[str, pathlib.Path] | None
    static_file_routes: list[tuple[str, pathlib.Path, str]] | None
    # For SSG: dist directory path
    dist_dir: pathlib.Path | None
    # Dev mode flag
    dev_mode: bool

def resolve_build_artifacts(
    app: WebComPyApp,
    build_config: WebComPyBuildConfig,
    *,
    dev_mode: bool = False,
    dist_dir: pathlib.Path | None = None,
) -> BuildArtifacts:
    """Resolve all build artifacts: dependencies, wheels, assets, lockfile."""
    # ... shared logic from both _generate.py and _server.py ...
```

**Rationale**: The current duplication between `_generate.py` (lines 38-283) and `_server.py` (lines 56-291) is ~200 lines of nearly identical code. Extracting it eliminates bugs from divergence and simplifies future changes. The `dev_mode` and `dist_dir` parameters control whether the function produces in-memory file maps (dev server) or writes to disk (SSG).

**What stays in each module**:
- `_server.py`: Route creation, Starlette app assembly, `send_html()`, SSE endpoint
- `_generate.py`: Dist directory creation, `.nojekyll`/`CNAME` writing, ASGITransport fetching, file writing
- `_build.py`: Dependency resolution, lockfile, WASM/runtime assets, wheel building

### Decision 5: create_asgi_app() mode parameter

**Chosen**: Add a `mode` parameter to `create_asgi_app()` with values `"dev"` (default) and `"ssg"`. In SSG mode, the SSE reload endpoint and dev-only cache headers are excluded.

```python
def create_asgi_app(
    app: WebComPyApp,
    build_config: WebComPyBuildConfig,
    *,
    mode: Literal["dev", "ssg"] = "dev",
) -> ASGIApp:
```

In SSG mode:
- No `/_webcompy_reload` SSE endpoint
- No dev-mode cache headers on wheel files
- `build_config.server.dev` is forced to `False`

**Rationale**: SSG doesn't need live reload or dev-mode cache headers. The mode parameter avoids creating a separate ASGI app constructor for SSG.

### Decision 6: generate_static_site() becomes async with asyncio.run() wrapper

**Chosen**: `generate_static_site()` becomes `async def generate_static_site()` internally. The CLI entry point wraps it with `asyncio.run()`.

```python
# webcompy/cli/_generate.py
async def generate_static_site(app: WebComPyApp | None = None):
    _, args = get_params()
    # ... build_config resolution ...
    artifacts = resolve_build_artifacts(app, build_config, dist_dir=dist_dir)
    asgi_app = create_asgi_app(app, build_config, mode="ssg")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=asgi_app),
        base_url="http://test",
    ) as client:
        # ... fetch routes and write HTML ...
```

```python
# webcompy/cli/__main__.py (CLI entry point)
# When "generate" subcommand is selected:
asyncio.run(generate_static_site())
```

**Rationale**: `asyncio.run()` is the standard way to run async code from a synchronous entry point. Since `generate_static_site()` is called from the CLI (which is synchronous), we need this wrapper. The function remains callable from Python code via `await generate_static_site(app)` or `asyncio.run(generate_static_site(app))`.

### Decision 7: Hash mode SSR — async pre-render with caching, separate from create_asgi_app()

**Chosen**: For hash mode apps (no history routing), `create_asgi_app()` remains synchronous and creates the ASGI app. A separate async function `_pre_render_hash_mode_html(app)` is called after `create_asgi_app()` returns. It enters the DI scope, sets the path to `/`, awaits `html_generator()`, and caches the result. The `send_html()` handler returns the cached HTML without awaiting on each request.

```python
# In _pre_render_hash_mode_html():
with app.di_scope:
    app.set_path("/")
    cached_html = await html_generator()  # Pre-render once

def create_asgi_app(app, build_config, mode="dev"):  # synchronous
    if app.router_mode == "hash":
        html = None  # Will be set after async pre-render
        async def send_html(_: Request):
            return HTMLResponse(html)
    # ... rest ...
    return Starlette(...)
```

**Rationale**: `uvicorn.run()` expects a synchronous ASGI app factory. Making `create_asgi_app()` async forces all callers (`run_server()`, `generate_static_site()`) to use `asyncio.run()` or `await`, which is unnecessary complexity for the common history-mode case. Separating hash-mode pre-rendering into a standalone function keeps the ASGI app creation simple and synchronous.

### Decision 8: CLI entry point — `run_server()` stays synchronous

**Chosen**: The `webcompy start` CLI command calls `create_asgi_app()` synchronously. For hash mode, it calls `asyncio.run(_pre_render_hash_mode_html(app))` after creation. For `webcompy generate`, the CLI calls `asyncio.run(generate_static_site())`.

**Rationale**: `run_server()` calls `uvicorn.run()` which manages its own event loop. `asyncio.run()` is only needed for the one-time hash-mode pre-render, not for creating the ASGI app itself.

## Risks / Trade-offs

- **ASGITransport overhead**: Creating an ASGI app and making HTTP requests for SSG is slightly more complex than direct `html_generator()` calls. However, the overhead is negligible compared to dependency resolution and wheel building, and the benefit (output parity) far outweighs the cost.
- **Pre-rendering hash-mode HTML**: For hash-mode apps, `_pre_render_hash_mode_html(app)` must be called after `create_asgi_app()` returns but before the server starts. The ordering dependency (create ASGI app → configure ServerFetchPort → pre-render → start server) must be maintained to ensure self-site fetch requests during pre-rendering work correctly.
- **httpx dependency for SSG**: `httpx` is already a project dependency (used by `ServerFetchPort`), so no new dependency is introduced.
- **Blocked paths during SSR**: When `ServerFetchPort` makes a fetch request during SSR, and the fetch target is a page route served by the same ASGI app, infinite recursion could occur. The `feat/server-fetch-port-asgi` change handles this by returning 500 for page routes when the request comes from `ServerFetchPort`.